import trainer.constants as cst
from trainer.custom_metrics_losses import mae_current_cycle, mae_remaining_cycles

from tensorflow.keras.layers import concatenate, Conv1D, Conv2D, Flatten, Input, Dense, MaxPool1D, MaxPool2D, Dropout
from tensorflow.keras.models import Model
from tensorflow.keras.optimizers import Adam


def create_keras_model(window_size, loss, hparams_config=None):
    """Creates the Keras model.
    
    Arguments
    window_size: Number of samples per row. Must match window_size 
    of the datasets that are used to fit/predict.
    
    loss: Loss function of the model.
    
    hparams_config: A dictionary of hyperparameters that can be used
    to test multiple configurations (hpo). Default is the 
    'hparams' dictionary that is defined at the beginning of this
    function. This dictionary is used for standard non-hpo jobs
    and for any parameter that is not defined in a hpo job.
    """
        
    # Default configuration
    hparams = {
        cst.CONV_FILTERS: 16,
        cst.CONV_KERNEL: 3,
        cst.CONV_KERNEL_2D: (3, 9),
        cst.CONV_STRIDE: 1,
        cst.CONV_ACTIVATION: "relu",
        cst.DENSE_NUM_UNITS: 32,
        cst.DENSE_NUM_UNITS_SCALAR: 100,
        cst.DENSE_ACTIVATION: "relu",
        cst.OUTPUT_ACTIVATION: "relu",
        cst.LEARNING_RATE: 0.001,
        cst.DROPOUT_RATE_CNN: 0.3,
    }
    # update hyperparameters with arguments from task_hyperparameter.py
    if hparams_config:
        hparams.update(hparams_config)

    # define Inputs
    qdlin_in = Input(shape=(window_size, cst.STEPS, cst.INPUT_DIM), name=cst.QDLIN_NAME)
    tdlin_in = Input(shape=(window_size, cst.STEPS, cst.INPUT_DIM), name=cst.TDLIN_NAME)
    ir_in = Input(shape=(window_size, cst.INPUT_DIM), name=cst.INTERNAL_RESISTANCE_NAME)
    dt_in = Input(shape=(window_size, cst.INPUT_DIM), name=cst.DISCHARGE_TIME_NAME)
    qd_in = Input(shape=(window_size, cst.INPUT_DIM), name=cst.QD_NAME)
    
    # ------ CNN PART FOR DETAIL FEATURES ------
    concat_detail = concatenate([qdlin_in, tdlin_in], axis=3)
    cnn_detail = Conv2D(filters=hparams[cst.CONV_FILTERS],
                        kernel_size=hparams[cst.CONV_KERNEL_2D],
                        strides=hparams[cst.CONV_STRIDE],
                        activation=hparams[cst.CONV_ACTIVATION],
                        padding='same',
                        name='cnn_detail')(concat_detail)
    maxpool_detail = MaxPool2D(pool_size=(1, 2), name='maxpool_detail')(cnn_detail)

    cnn_detail2 = Conv2D(filters=hparams[cst.CONV_FILTERS] * 2,
                         kernel_size=hparams[cst.CONV_KERNEL_2D],
                         strides=hparams[cst.CONV_STRIDE],
                         activation=hparams[cst.CONV_ACTIVATION],
                         padding='same',
                         name='cnn_detail2')(maxpool_detail)
    maxpool_detail2 = MaxPool2D(pool_size=(1, 2), name='maxpool_detail2')(cnn_detail2)

    cnn_detail3 = Conv2D(filters=hparams[cst.CONV_FILTERS] * 4,
                         kernel_size=hparams[cst.CONV_KERNEL_2D],
                         strides=hparams[cst.CONV_STRIDE],
                         activation=hparams[cst.CONV_ACTIVATION],
                         padding='same',
                         name='cnn_detail3')(maxpool_detail2)
    maxpool_detail3 = MaxPool2D(pool_size=(2, 2), name='maxpool_detail3')(cnn_detail3)
    
    cnn_detail4 = Conv2D(filters=hparams[cst.CONV_FILTERS] * 4,
                         kernel_size=hparams[cst.CONV_KERNEL_2D],
                         strides=hparams[cst.CONV_STRIDE],
                         activation=hparams[cst.CONV_ACTIVATION],
                         padding='same',
                         name='cnn_detail4')(maxpool_detail3)
    maxpool_detail4 = MaxPool2D(pool_size=(2, 2), name='maxpool_detail4')(cnn_detail4)
    
    flat_detail = Flatten(name='flat_detail')(maxpool_detail4)
    dropout_detail = Dropout(rate=hparams[cst.DROPOUT_RATE_CNN], name='dropout_detail')(flat_detail)

    # ------ CNN PART FOR SCALAR FEATURES ------
    # Concatenate scalar features in the window direction to produce a shape (None, 60, 1)
    concat_scalar = concatenate([ir_in, dt_in, qd_in], axis=2, name='concat_scalar')
    cnn_scalar = Conv1D(filters=hparams[cst.CONV_FILTERS],
                        kernel_size=hparams[cst.CONV_KERNEL],
                        strides=hparams[cst.CONV_STRIDE],
                        activation=hparams[cst.CONV_ACTIVATION],
                        padding='same',
                        name='cnn_scalar')(concat_scalar)
    cnn_scalar2 = Conv1D(filters=hparams[cst.CONV_FILTERS] * 2,
                         kernel_size=hparams[cst.CONV_KERNEL],
                         strides=hparams[cst.CONV_STRIDE],
                         activation=hparams[cst.CONV_ACTIVATION],
                         padding='same',
                         name='cnn_scalar2')(cnn_scalar)
    maxpool_scalar = MaxPool1D(name='maxpool_scalar')(cnn_scalar2)
    flat_scalar = Flatten(name='flat_scalar')(maxpool_scalar)
    dropout_scalar = Dropout(rate=hparams[cst.DROPOUT_RATE_CNN], name='dropout_scalar')(flat_scalar)
    
    concat_all = concatenate([dropout_detail, dropout_scalar], axis=1, name="concat_all")
    
    hidden_dense = Dense(128,
                         activation=hparams[cst.DENSE_ACTIVATION],
                         name='hidden_dense',)(concat_all)
    hidden_dense2 = Dense(hparams[cst.DENSE_NUM_UNITS],
                          activation=hparams[cst.DENSE_ACTIVATION],
                          name='hidden_dense2',)(hidden_dense)
    # Relu activation on the last layer for striclty positive outputs
    main_output = Dense(2, name='output', activation=hparams[cst.OUTPUT_ACTIVATION])(hidden_dense2)

    model = Model(inputs=[qdlin_in, tdlin_in, ir_in, dt_in, qd_in], outputs=[main_output])
    
    metrics_list = [mae_current_cycle, mae_remaining_cycles]
    
    model.compile(loss=loss, optimizer=Adam(lr=hparams[cst.LEARNING_RATE], clipnorm=1.), metrics=metrics_list)

    return model