function postAllWorkflowRuns() {
    var document = __.response.getBody();

    switch(document.type) {
        case "JobPartitionRun":
            handleJobPartitionRun(document);
            break;
        default:
            break;
    }

    return;

    // Handlers

    function handleJobPartitionRun(jobPartitionRun) {

        // query for WorkflowRun document
        var runId = jobPartitionRun.run_id
        var jobId = jobPartitionRun.job_id
        var recordType = "WorkflowRun"
        var filterQuery = `SELECT * FROM r WHERE r.run_id = "${runId}" AND r.type = "${recordType}"`;
        var accept = __.queryDocuments(__.getSelfLink(), filterQuery,
            updateJobRun);

        if (!accept) throw "Unable to update WorkflowRun, abort";

        function updateJobRun(err, documents, responseOptions) {
            if (err) throw new Error("Error: " + err.message);

            if (documents.length < 1) throw 'Unable to find WorkflowRun document';
            if (documents.length > 1) throw 'Found more than one WorkflowRun document';
            var workflowRun = documents[0];

            job = workflowRun.jobs.find(j => j.job_id == jobId);
            if(!job) throw `Unable to find job ${jobId} in WorkflowRun document`;

            if (jobPartitionRun.status_history.length > 1) {
                let prevStatus = jobPartitionRun.status_history.slice(-2)[0].status

                if(prevStatus in job.job_partition_counts) {
                    job.job_partition_counts[prevStatus] -= 1
                }
            }
            if(!(jobPartitionRun.status in job.job_partition_counts)) {
                job.job_partition_counts[jobPartitionRun.status] = 0
            }
            job.job_partition_counts[jobPartitionRun.status] += 1

            var accept = __.replaceDocument(workflowRun._self,
                workflowRun, function (err, docReplaced) {
                    if (err) throw "Unable to update WorkflowRun, abort";
                });
            if (!accept) throw "Unable to update WorkflowRun, abort";
            return;
        }
    }
}