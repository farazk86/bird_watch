import numpy as np
from keras.preprocessing.image import ImageDataGenerator, img_to_array, load_img
from keras.models import Sequential, Model
from keras.layers import Dropout, Flatten, Dense, GlobalAveragePooling2D, Input
from keras.applications.inception_v3 import InceptionV3
from keras import optimizers
from keras.utils.np_utils import to_categorical
from keras.callbacks import ModelCheckpoint
import matplotlib.pyplot as plt
import math

# dimensions of our images.
img_width, img_height = 400, 400

top_model_weights_path = 'data/models/bottleneck_fc_model_006.h5'
train_data_dir = 'data/train'
validation_data_dir = 'data/validation'

final_model_path ='data/models/final_model_006.h5'

# number of epochs to train top model
epochs = 100
# batch size used by flow_from_directory and predict_generator
batch_size = 64

# prepare data augmentation configuration
datagen = ImageDataGenerator(
                    rescale=1. / 255,
                    rotation_range=40,
                    shear_range=0.2,
                    zoom_range=0.2,
                    horizontal_flip=True,
                    fill_mode='nearest',
                    validation_split=0.1)

train_generator = datagen.flow_from_directory(
                    train_data_dir,
                    target_size=(img_width, img_height),
                    batch_size=batch_size,
                    class_mode='categorical',
                    interpolation='lanczos',
                    subset='training')

validation_generator = datagen.flow_from_directory(
                    train_data_dir,
                    target_size=(img_width, img_height),
                    batch_size=batch_size,
                    class_mode='categorical',
                    interpolation='lanczos',
                    subset='validation')

nb_train_samples = len(train_generator.filenames)
nb_validation_samples = len(validation_generator.filenames)
num_classes = len(train_generator.class_indices)

print("[Info] Dataset stats: Training: {} Validation: {}".format(nb_train_samples, nb_validation_samples))
print("[Info] Number of Classes: {}".format(num_classes))
print("[Info] Class Labels: {}".format(train_generator.class_indices))

train_steps = int(math.ceil(nb_train_samples / batch_size))
validation_steps = int(math.ceil(nb_validation_samples / batch_size))

input_tensor = Input(shape=(img_width, img_height, 3))

# build the InceptionV3 network
base_model = InceptionV3(weights='imagenet', include_top=False, input_tensor=input_tensor)
print("[Info] Model loaded.")

i = Input(shape=base_model.output_shape[1:])
x = GlobalAveragePooling2D()(i)
x = Dense(1024, activation='relu')(x)
x = Dropout(0.3)(x)
pred = Dense(num_classes, activation='softmax')(x)
top_model = Model(inputs=i, outputs=pred)

# note that it is necessary to start with a fully-trained
# classifier, including the top classifier,
# in order to successfully do fine-tuning
top_model.load_weights(top_model_weights_path)

# add the model on top of the convolutional base
model = Model(inputs=base_model.input, outputs=top_model(base_model.output))

# set the first 280 layers (up to the last conv block)
# to non-trainable (weights will not be updated)
for layer in model.layers[:280]:
    layer.trainable = False

# compile the model with a SGD/momentum optimizer
# and a very slow learning rate.
model.compile(loss='categorical_crossentropy',
              optimizer=optimizers.SGD(lr=1e-4, momentum=0.9),
              metrics=['accuracy'])

filepath="data/models/checkpoints/model-{epoch:02d}-{val_acc:.2f}.h5"
checkpoint = ModelCheckpoint(filepath, monitor='val_acc', verbose=1, save_best_only=True, save_weights_only=False, mode='max')
callbacks_list = [checkpoint]

history = model.fit_generator(
    train_generator,
    steps_per_epoch=train_steps,
    epochs=epochs,
    validation_data=validation_generator,
    validation_steps=validation_steps,
    callbacks=callbacks_list)

(eval_loss, eval_accuracy) = model.evaluate_generator(
    validation_generator,
    steps=validation_steps)

model.save(final_model_path)

print("\n")

print("[INFO] accuracy: {:.2f}%".format(eval_accuracy * 100))
print("[INFO] Loss: {}".format(eval_loss))

plt.style.use('ggplot')

plt.figure(1)

# summarize history for accuracy

plt.subplot(211)
plt.plot(history.history['acc'])
plt.plot(history.history['val_acc'])
plt.title('Model Accuracy')
plt.ylabel('Accuracy')
plt.xlabel('Epoch')
plt.legend(['Training', 'Validation'], loc='lower right')

# summarize history for loss

plt.subplot(212)
plt.plot(history.history['loss'])
plt.plot(history.history['val_loss'])
plt.title('Model Loss')
plt.ylabel('Loss')
plt.xlabel('Epoch')
plt.legend(['Training', 'Validation'], loc='upper right')

plt.tight_layout()
plt.show()