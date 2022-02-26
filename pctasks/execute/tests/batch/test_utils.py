from pctasks.execute.batch.utils import make_valid_batch_id


def test_make_valid_job_id():
    assert (
        make_valid_batch_id("some-job/job_ok/!this/is/not/valid")
        == "some-job-job_ok--this-is-not-valid"
    )
    long_job_id = "test-chars" * 7
    assert len(make_valid_batch_id(long_job_id)) == 64
