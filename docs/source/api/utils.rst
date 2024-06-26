.. role:: hidden
   :class: hidden-section

CoLLiE.utils
===================================

.. contents:: CoLLiE.utils
   :depth: 2
   :local:
   :backlinks: top

.. currentmodule:: collie.utils.dist_utils

Dist Utils
----------------

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: classtemplate.rst

   Env

.. currentmodule:: collie.utils
.. autosummary::
   :toctree: generated
   :nosignatures:

   setup_distribution
   setup_ds_engine
   set_seed
   broadcast_tensor
   zero3_load_state_dict
   is_zero3_enabled

Utils
----------------

.. autosummary::
   :toctree: generated
   :nosignatures:

   find_tensors
   apply_to_collection
   dict_as_params
   concat_tensor

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: classtemplate.rst

   progress

Data Provider
----------------

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: classtemplate.rst

   BaseProvider
   GradioProvider
   DashProvider

Monitor
----------------

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: classtemplate.rst

   BaseMonitor
   StepTimeMonitor
   TGSMonitor
   MemoryMonitor
   LossMonitor
   EvalMonitor
   LRMonitor

Padder
----------------

.. autosummary::
   :toctree: generated
   :nosignatures:
   :template: classtemplate.rst

   ColliePadder