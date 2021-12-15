import math

import tensorflow as tf
from tensorflow.keras import Sequential, backend as K
from tensorflow.keras.layers import Dense
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.metrics import MeanIoU
from tensorflow.keras.losses import BinaryCrossentropy
from tensorflow.keras.callbacks import LearningRateScheduler


# learning rate decay
def step_decay(epoch, initial_lrate=0.001, drop=0.7, epochs_drop=10.0):
    lrate = initial_lrate * math.pow(drop, math.floor((1 + epoch) / epochs_drop))
    return lrate


class LossHistory(tf.keras.callbacks.Callback):
    def on_train_begin(self, logs={}):
        self.losses = []
        self.lr = []

    def on_epoch_end(self, batch, logs={}):
        self.losses.append(logs.get('loss'))
        self.lr.append(step_decay(len(self.losses)))
        print(step_decay(len(self.losses)))


class NeuzzModel:
    def __init__(self, epochs=5, lr=0.0001):
        self.epochs = epochs
        self.lr = lr
        self.model = None

    def initialize_model(self, input_width, num_classes, network):
        model = Sequential()
        model.add(Dense(network[0], input_dim=input_width, activation='relu'))
        for dim in network[1:]:
            model.add(Dense(dim, activation='relu'))
        model.add(Dense(num_classes, activation='relu'))

        self.model = model
        # todo: validate loss function
        self.model.compile(loss=BinaryCrossentropy(from_logits=True), optimizer=Adam(learning_rate=self.lr),
                           metrics=[MeanIoU(num_classes=num_classes)])
        self.model.summary()

    @property
    def is_model_created(self):
        return self.model is not None

    def train(self, data, val_data):
        K.set_value(self.model.optimizer.learning_rate, 0.0001)
        self.model.fit(*data,
                       callbacks=[LossHistory(), LearningRateScheduler(step_decay)],
                       epochs=self.epochs, verbose=1, validation_data=tuple(val_data),
                       sample_weight=data.weights)

    def gradient(self, input, modded_y_test):
        input = tf.convert_to_tensor(input.reshape(1, -1), dtype=tf.float32)
        modded_y_test = tf.convert_to_tensor(modded_y_test.reshape(1, -1), dtype=tf.float32)

        with tf.GradientTape() as tape:
            tape.watch(input)
            predictions = self.model(input, training=False)
            loss = self.model.loss(modded_y_test, y_pred=predictions)
        grad = tape.gradient(loss, input)
        return grad.numpy()
