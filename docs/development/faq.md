# Frequently Asked Questions

## When to use docker-compose vs cluster for workflows?

PCTasks has two mechanisms to submit workflows to the development environment: one that runs through the docker-compose services
started via `scripts/server`, and another that runs inside the Kind cluster. The docker-compose setup executes workflows inside the server
process and executes tasks through a
light-weight mock of Azure Batch in the `local-dev-endpoints` service, while the Kind Cluster executes both workflows and tasks
via the Argo installation in the Kind cluster. The docker-compose endpoint is useful for lighter-weight testing, and is what
the unit tests of PCTasks work against. When doing internal development on PCTasks, this endpoint is useful to utilize without
having to update the Kind cluster with the latest docker images and code. On the other hand, the Kind cluster is a more
accurate representation of the eventual deployed PCTasks system, and therefore is good for end to end testing. The integration tests
for PCTasks utilize the Kind cluster for this purpose. If you are not modifying the internals of PCTasks, e.g. if you are creating datasets,
then it's recommended to test running workflows against the Kind cluster setup.
