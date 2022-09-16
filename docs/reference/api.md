# API Reference

```{currentmodule} pctasks
```

## `pctasks.core`

The `pctasks.core` package provides core functionality used by the rest of `pctasks`.

### `pctasks.core.storage`

Helper functions and classes for dealing with local or remote file systems.

```{eval-rst}
.. autosummary::
   :toctree: ./generated/
   :recursive:

   pctasks.core.storage.Storage
   pctasks.core.storage.StorageFactory
   pctasks.core.storage.blob.BlobUri
   pctasks.core.storage.blob.BlobStorage
```

## `pctasks.task`

The `pctasks.task` package provides functionality for building tasks to be executed in PCTasks.

```{eval-rst}
.. autosummary::
   :toctree: ./generated/
   :recursive:

   pctasks.task.task.Task
   pctasks.task.task.TaskContext
```

## `pctasks.dataset`

The `pctasks.dataset` package provides functionality for defining PCTasks workflows that process STAC Items and Collections.

```{eval-rst}
.. autosummary::
   :toctree: ./generated/
   :recursive:

   pctasks.dataset.collection.Collection
```
