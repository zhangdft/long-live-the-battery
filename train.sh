# standard args

BUCKET='ion_age_bucket'
REGION='europe-west1'

PACKAGE_PATH='trainer/'
MODULE_NAME='trainer.task'

PACKAGE_STAGING_PATH="gs://${BUCKET}"
JOB_DIR="gs://${BUCKET}/jobs/"

now=$(date +"%Y%m%d_%H%M%S")
JOB_NAME="ion_age_$now"

# user-specified args

TFRECORDS_DIR="gs://${BUCKET}/data/tfrecords/"


gcloud ai-platform jobs submit training $JOB_NAME \
    --staging-bucket $PACKAGE_STAGING_PATH \
    --job-dir $JOB_DIR  \
    --package-path $PACKAGE_PATH \
    --module-name $MODULE_NAME \
    --region $REGION \
    -- \
    --tfrecords-dir $TFRECORDS_DIR \
    # --user_second_arg=second_arg_value