function postAllWorkflows() {
    var document = __.response.getBody();

    switch(document.type) {
        case "WorkflowRun":
            handleWorkflowRun(document);
            break;
        default:
            break;
    }

    return;

    // Handlers

    function handleWorkflowRun(workflowRun) {

        // query for WorkflowRun document
        var workflowId = workflowRun.workflow_id
        var recordType = "Workflow"
        var filterQuery = `SELECT * FROM r WHERE r.workflow_id = "${workflowId}" AND r.type = "${recordType}"`;
        var accept = __.queryDocuments(__.getSelfLink(), filterQuery,
            updateJobRun);

        if (!accept) throw "Unable to update Workflow, abort";

        function updateJobRun(err, documents, responseOptions) {
            if (err) throw new Error("Error: " + err.message);

            if (documents.length < 1) throw 'Unable to find Workflow document';
            if (documents.length > 1) throw 'Found more than one Workflow document';
            var workflow = documents[0];

            if (workflowRun.status_history.length > 1) {
                let prevStatus = workflowRun.status_history.slice(-2)[0].status

                if(prevStatus in workflow.workflow_run_counts) {
                    workflow.workflow_run_counts[prevStatus] -= 1
                }
            }
            if(!(workflowRun.status in workflow.workflow_run_counts)) {
                workflow.workflow_run_counts[workflowRun.status] = 0
            }
            workflow.workflow_run_counts[workflowRun.status] += 1

            var accept = __.replaceDocument(workflow._self,
                workflow, function (err, docReplaced) {
                    if (err) throw "Unable to update Workflow, abort";
                });
            if (!accept) throw "Unable to update Workflow, abort";
            return;
        }
    }
}