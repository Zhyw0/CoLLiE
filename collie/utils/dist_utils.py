import os
import copy
import json
import re
import subprocess

import torch
import deepspeed
from deepspeed.runtime.utils import set_random_seed
from deepspeed.runtime.zero.stage_1_and_2 import DeepSpeedZeroOptimizer
from deepspeed.accelerator import get_accelerator
from megatron.core import parallel_state, tensor_parallel

def setup_distributation(args) -> None:
    """Setup the distributed training environment.
    Support two kinds of distributed training:
    1. launch from torchrun
        eg: torchrun --standalone --nproc_per_node=8 train.py
    2. launch from slurm
        eg. srun --partition=xxx --gres=gpu:8 --ntasks=8 --ntasks-per-node=8 --job-name=xxx --kill-on-bad-exit=1 train.py
    """
    if torch.distributed.is_initialized():
        return
    patch_deepspeed(args);patch_megatron()
    if "WORLD_SIZE" in os.environ.keys():
        # launch from pytorch
        master_addr = os.environ.get("MASTER_ADDR", "localhost")
        master_port = os.environ.get("MASTER_PORT", "27001")
    elif "SLURM_JOB_NODELIST" in os.environ.keys():
        # launch from slurm
        node_list_str = os.environ["SLURM_JOB_NODELIST"]
        node_list = []
        result = re.search(r"\[(.*?)\]", node_list_str)
        if result is None:
            node_list.append(node_list_str)
        else:
            node_list.extend([item for item in result.groups(1)[0].split(",")])
            for i in node_list:
                if "-" in i:
                    node_list.extend(list(map(lambda x: f"{x}", range(int(i.split("-")[0]), int(i.split("-")[1]) + 1))))
                    node_list.remove(i)
            node_list = list(map(lambda x: re.sub(r"\[(.*?)\]", x, node_list_str), node_list))
            node_list = sorted(node_list)
            master_addr = node_list[0]
            result = subprocess.run(["scontrol", "show", "node", master_addr], capture_output=True)
            result = re.search(r"NodeAddr=(.*?)\s", result.stdout.decode())
            if result:
                master_addr = result.groups(1)[0]
            if "MASTER_PORT" in os.environ.keys():
                master_port = os.environ["MASTER_PORT"]
            else:
                master_port = 27002
            os.environ["LOCAL_RANK"] = os.environ["SLURM_LOCALID"]
            os.environ["RANK"] = os.environ["SLURM_PROCID"]
            os.environ["WORLD_SIZE"] = os.environ["SLURM_NTASKS"]
    deepspeed.init_distributed(dist_backend='nccl', 
                                init_method="tcp://{}:{}".format(
                                    master_addr, 
                                    master_port),
                                world_size=int(os.environ["WORLD_SIZE"]),
                                rank=int(os.environ["RANK"]))
    parallel_state.initialize_model_parallel(tensor_model_parallel_size=args.tp_size)
    # random seed has to be set after deepspeed.init_distributed
    set_seed(args)
    torch.cuda.set_device(torch.device('cuda:{}'.format(os.environ["LOCAL_RANK"])))
    os.environ["COLLIE_PP_RANK"] = "0"
    os.environ["COLLIE_TP_RANK"] = str(parallel_state.get_tensor_model_parallel_rank())
    os.environ["COLLIE_DP_RANK"] = str(parallel_state.get_data_parallel_rank())

def set_seed(args):
    """Set random seed for reproducibility.
    """
    tensor_parallel.model_parallel_cuda_manual_seed(args.seed)
    set_random_seed(args.seed)

def patch_deepspeed(args):
    if hasattr(args, "ds_config") \
        and "zero_optimization" in args.ds_config.keys() \
            and "offload_optimizer" in args.ds_config["zero_optimization"].keys() \
                and "pin_memory" in args.ds_config["zero_optimization"]["offload_optimizer"].keys() \
                    and not args.ds_config["zero_optimization"]["offload_optimizer"]["pin_memory"]:
        get_accelerator().pin_memory = lambda x: x
    if hasattr(args, "ds_config") \
        and "zero_optimization" in args.ds_config.keys() \
            and "offload_param" in args.ds_config["zero_optimization"].keys() \
                and "pin_memory" in args.ds_config["zero_optimization"]["offload_param"].keys() \
                    and not args.ds_config["zero_optimization"]["offload_param"]["pin_memory"]:
        get_accelerator().pin_memory = lambda x: x
    raw_init = copy.deepcopy(DeepSpeedZeroOptimizer.__init__)
    def safe_init(self, *args, **kwargs):
        while True:
            try:
                raw_init(self, *args, **kwargs)
                break
            except RuntimeError as e:
                continue
    DeepSpeedZeroOptimizer.__init__ = safe_init
    raw_initialize_optimizer_states = copy.deepcopy(DeepSpeedZeroOptimizer.initialize_optimizer_states)
    def safe_initialize_optimizer_states(self, *args, **kwargs):
            while True:
                try:
                    raw_initialize_optimizer_states(self, *args, **kwargs)
                    break
                except RuntimeError as e:
                    continue
    DeepSpeedZeroOptimizer.initialize_optimizer_states = safe_initialize_optimizer_states
    
def patch_megatron():
    parallel_state.get_model_parallel_world_size = lambda: parallel_state.get_tensor_model_parallel_world_size()
    parallel_state.get_model_parallel_rank = lambda: parallel_state.get_tensor_model_parallel_rank()

def is_pipeline():
    return "COLLIE_PP_PARTS" in os.environ.keys()

def pipline_parts():
    if "COLLIE_PP_PARTS" in os.environ.keys():
        parts = json.loads(os.environ["COLLIE_PP_PARTS"])
    else:
        parts = None

    return parts

def pipline_layers_idx():
    """
    :return: list or None
    """
    parts = pipline_parts()
    if parts is None:
        return None
    else:
        stage = get_pp_rank()
        return list(range(parts[stage], parts[stage + 1]))

def get_dp_rank():
    return int(os.getenv("COLLIE_DP_RANK", "0"))

def get_tp_rank():
    return int(os.getenv("COLLIE_TP_RANK", "0"))

def get_pp_rank():
    return int(os.getenv("COLLIE_PP_RANK", "0"))