# Chunking

This document describes how PCTasks uses "chunk files" as a mechanism to control parallelization and optimize processing
of large datasets.

## Why chunk?
Sometimes we need to run workflows over very large sets of data. If we need to create STAC Items for, say, 10 million scenes, then either we
A. have a single task run over all 10 million scenes (no), B. parallelize over each scene, and create 10 million parallelizable tasks, or C. we
group those scenes into sets - call them "chunks", and then process each of the chunks in parallel. PCTasks uses chunks and chunk files to
implement option C.

Parallelizing over each of 10 million scenes would require for example 10 million Azure Batch tasks. It would require the PCTasks workflow execution
process to track the output of each of those 10 million tasks. This can overload services and create untenable bottlenecks.

Other systems, like [Cirrus](https://github.com/cirrus-geo/cirrus-geo), solve this problem by having a queue based mechanism that is fed individual
scene information to a queue, with workers pulling from a centralized queue. This is a possible future execution architecture option for PCTasks,
but currently the architecture does not support this type of approach.

Instead, we rely on precursor tasks to create "chunk files".

## Chunk files
A chunk file is simply a text file that contains asset URIs, one per line. Chunk files are configured in PCTasks datasets, which determines how many asset URIs are contained in each chunk file.

Each asset URI represents a single STAC Item. The asset URI is not exclusively the asset of the Item, nor does it even have to be referenced by the
eventual STAC Item it represents. However it is required that a single asset URI can uniquely identify a single STAC Item, i.e. that the representative asset URI and the STAC Item have a 1-to-1 relationship.

Chunk options also dictate which files are the representative asset URIs. Here is a chunks setting that lists all available options:

```yaml
chunks:
  options:
    chunk_length: 1000  # Each chunk file will contain max 1000 URIs
    name_starts_with: prefix/  # Only include asset URIs that start with this string.
    since: 2022-08-01  # Only include assets that have been modified since this time.
    extensions: [.tif]  # Only include asset URIs with an extension in this list.
    ends_with: manifest.xml  # Only include asset URIs that end with this string.
    matches: .*/scene-\d+.tif  # Only include asset URIs that match this regex."""
    max_depth: 10  # Maximum number of directories to descend into.
    min_depth: 10  # Minimum number of directories to descend into. Useful for listing a subfolder.
    list_folders: true  # Whether to list files (the default) or folders instead of files.
    chunk_file_name: uri-list  # Chunk file name.
    chunk_extension: .csv  # Extensions of the chunk file names.
    limit: 10  # Limit the number of URIs to process. Useful for testing.
```

## Splits
Splits are used to parallelize the creation of chunk files. This is useful because even listing blobs for
storage accounts containing millions of files takes a long time. Splits will create URIs for folder names
(blob prefixes) to a certain depth. Then chunk files can be created for each prefix in parallel, ensuring
each URI in each chunk file is only listed in a single chunk file.

Splits are configured as part of the chunks configuration. For example:

```yaml
chunks:
  splits:
    - depth: 3
    - prefix: large-subfolder/
      depth: 4
```

In the above case, the first split means that the Storage will be walked for folders of depth 3 from the root,
and those URIs will be output for use in a `foreach` block to parallelize chunk file creation. But because
a second split configuration is defined, any folder starting with `large-subfolder/` will be generated
with a depth of 4. Enabling split configs to further split certain subfolders is useful in cases where
the number of files is not evenly distributed through subfolders, so you want to split on certain branches
of the subfolders more than others.