import numpy as np
import tensorflow as tf
from tensorflow.keras import Sequential
from tensorflow.keras.layers import Dense
from tensorflow.keras.losses import MeanSquaredError


def create_ds():
    X = np.random.uniform(size=(10000, 200))
    y_ = np.sin(X).sum(axis=1)
    y = np.array((y_, 2 * y_, 4 * y_, y_ * y_)).T

    return (X[:8000], y[:8000]), (X[8000:], y[8000:])


(x_train, y_train), (x_test, y_test) = create_ds()
x_val, x_train = np.split(x_train, [40])
y_val, y_train = np.split(y_train, [40])

model = Sequential([Dense(100, input_dim=200, activation='relu'),
                    Dense(4)])

if __name__ == '__main__':
    loss_obj = MeanSquaredError()
    model.compile('adam', loss_obj)
    model.summary()
    model.fit(x_train, y_train, epochs=20, validation_data=[x_val, y_val])

    img = tf.convert_to_tensor(x_test[:1], dtype=tf.float32)
    with tf.GradientTape() as tape:
        tape.watch(img)
        predictions = model(img, training=False)
        loss = loss_obj(y_test[:1], predictions)
    grad = tape.gradient(loss, img)
    print(grad)
