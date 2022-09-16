# Storage

PCTasks uses an abstraction over storage to make working with local files, Azure Blob Storage, and SAS Tokens easier. This user
guide goes over some key concepts you should know when working with `pctasks.core.storage` functionality.

## The `Storage` class

The [](../reference/generated/pctasks.core.storage.Storage) class is the main abstraction over file systems. You can use that instance to read and write files, walk files, get file info, etc. See the reference documentation for a list of all the methods provided.

Currently there are storage implementations for the local file system and Azure Blob Storage.

## Paths vs URIs vs URLs vs Authenticated URLs

These terms, which generally mean similar things, have specific definitions and differences in PCTasks.

### path

A "path" is a file location description that is relative to the root of the `Storage` instance. For instance, if my
storage root is for a storage account "myaccount", container "mycontainer", with a path prefix of "blobs/", then
the path "file1.txt" would be represented by the URI of "blob://myaccount/mycontainer/blobs/file1.txt".

### URI

A URI is a resource ID that can use non-http schemes. This is generally use to reference Azure Blob Storage locations
more easily than their full Azure URLs. For instance, `blob://myaccount/mycontainer/blobs/file1.txt` is a URI
that would translate to the URL <https://myaccount.blob.core.windows.net/mycontainer/blobs/file1.txt>.

### URL

A URL is an http schemed resource ID.

### Authenticated URL

An authenticated URL is a URL that is appended with a token. This is currently only applicable to Azure Storage,
in which a SAS token is appended to the URL. You can get the authenticated URL with the `Storage.get_authenticated_url`
method, but only if that Azure Storage instance was created using a SAS token.

(StorageFactory)=
## `StorageFactory`

A `StorageFactory` can create `Storage` instances given a URI. It can be configured with SAS tokens so that
any URI requesting a storage account and container for which the factory has a token for, that Storage instance
will be created using that token.

You can also call `get_storage_for_file` on the factory returns a tuple where the first element is the `Storage` instance
and the second is the path that represents the file for that storage.

You can also skip instantiating a `StorageFactory` instance and use utility methods to create storage from a default instance:

```python
from pctasks.core.storage import get_storage

storage = get_storage("/home/user")
```

and

```python
from pctasks.core.storage import get_storage_for_file

storage, path = get_storage_for_file("blob://myaccount/mycontainer/blobs/file1.txt")
assert storage.get_uri() == "blob://myaccount/mycontainer/blobs"
assert path == "file1.txt"
```