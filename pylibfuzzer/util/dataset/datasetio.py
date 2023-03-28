import logging
import os
import random
import re
import shutil
import string
import struct
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
from more_itertools import flatten
from keras.layers import TextVectorization
from tqdm import tqdm
import tensorflow as tf

from .dataset import Dataset

logger = logging.getLogger(__name__)


class DatasetIO:
    """
    Convenience class to handle importing and exporting of the data.
    When collecting data this class is used as a contextmanager. see Runner class for usage.
    """

    def __init__(self, logdir, dry_run=False):
        self.logdir = logdir
        self.dry_run = dry_run
        self.dataset_dir = TemporaryDirectory()

    def __enter__(self):
        self.dataset_dir.__enter__()
        return self

    def collect(self, idx, input, cov):
        if not self.dry_run:
            with open(Path(self.dataset_dir.name) / f"input_{idx}", 'wb') as f:
                f.write(input)
            with open(Path(self.dataset_dir.name) / f"cov_{idx}", 'wb') as f:
                f.write(cov)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.dry_run:
            logger.info('Compressing the dataset into a zip archive')
            shutil.make_archive(str(self.logdir / 'dataset'), 'zip', self.dataset_dir.name)
        self.dataset_dir.__exit__(exc_type, exc_val, exc_tb)

    @staticmethod
    def load(dataset_path: str, max_input_len=500):
        """
        Takes dataset.zip and loads the data into dataset class
        """

        logger.info("loading dataset")
        dataset = np.load(dataset_path)

        X, y = [], []
        for inp in dataset.items():
            if 'input' in inp[0]:
                filebytes = inp[1]
                X.append(filebytes + bytes(bytearray(max_input_len - len(filebytes))))
                try:
                    filename = "cov_" + inp[0].split('_')[1]
                    y.append(dataset[filename])
                except KeyError as ke:
                    raise RuntimeError("Problem while loading dataset: can't find related coverage file:", ke)

        yy = np.array([np.frombuffer(c, dtype=np.uint8) for c in y]).astype(np.float64)
        return Dataset(X=np.array([np.frombuffer(b, dtype=np.uint8) for b in X]), y=yy)

    @staticmethod
    def load_jqf(dataset_path: str):
        """
        loads JQF dataset: takes dataset.zip and loads the data into dataset class
        """

        logger.info("loading jqf dataset")

        # prepare inputs
        inputs = []
        pbar = tqdm(total=50000)
        with open(os.path.join(dataset_path, "events.bin"), "rb") as f:
            while length := f.read(4):
                n = struct.unpack(">i", length)[0]
                pbar.update(1)
                inputs.append(" ".join(map(str, flatten(struct.iter_unpack(">h", f.read(n * 2))))))
        pbar.close()

        # prepare outputs
        outputs = []
        corpus = os.path.join(dataset_path, "corpus")
        for fname in tqdm(sorted(os.listdir(corpus))):
            with open(os.path.join(corpus, fname), "rb") as file:
                outputs.append(" ".join(map(str, flatten(struct.iter_unpack(">B", file.read())))))

        print(inputs[0])
        print(len(inputs))
        print(outputs[0])
        print(len(outputs))

        return zip(inputs, outputs)

    @classmethod
    def preprocess_data_transformer(cls, zip_pairs: zip):
        text_pairs = []
        for inp, out in zip_pairs:
            out = "[start] " + out + " [end]"
            text_pairs.append((inp, out))

        random.shuffle(text_pairs)
        num_val_samples = int(0.15 * len(text_pairs))
        num_train_samples = len(text_pairs) - 2 * num_val_samples
        train_pairs = text_pairs[:num_train_samples]
        val_pairs = text_pairs[num_train_samples: num_train_samples + num_val_samples]
        test_pairs = text_pairs[num_train_samples + num_val_samples:]

        print(f"{len(text_pairs)} total pairs")
        print(f"{len(train_pairs)} training pairs")
        print(f"{len(val_pairs)} validation pairs")
        print(f"{len(test_pairs)} test pairs")

        strip_chars = string.punctuation + "¿"
        strip_chars = strip_chars.replace("[", "")
        strip_chars = strip_chars.replace("]", "")

        vocab_size = 100
        sequence_length = 20
        batch_size = 64

        def custom_standardization(input_string):
            lowercase = tf.strings.lower(input_string)
            return tf.strings.regex_replace(lowercase, "[%s]" % re.escape(strip_chars), "")

        eng_vectorization = TextVectorization(
            max_tokens=vocab_size, output_mode="int", output_sequence_length=sequence_length,
        )
        spa_vectorization = TextVectorization(
            max_tokens=vocab_size,
            output_mode="int",
            output_sequence_length=sequence_length + 1,
            standardize=custom_standardization,
        )
        train_eng_texts = [pair[0] for pair in train_pairs]
        train_spa_texts = [pair[1] for pair in train_pairs]
        eng_vectorization.adapt(train_eng_texts)
        spa_vectorization.adapt(train_spa_texts)

        def format_dataset(eng, spa):
            eng = eng_vectorization(eng)
            spa = spa_vectorization(spa)
            return {"encoder_inputs": eng, "decoder_inputs": spa[:, :-1], }, spa[:, 1:]

        def make_dataset(pairs):
            eng_texts, spa_texts = zip(*pairs)
            eng_texts = list(eng_texts)
            spa_texts = list(spa_texts)
            dataset = tf.data.Dataset.from_tensor_slices((eng_texts, spa_texts))
            dataset = dataset.batch(batch_size)
            dataset = dataset.map(format_dataset)
            return dataset.shuffle(2048).prefetch(16).cache()

        train_ds = make_dataset(train_pairs)
        val_ds = make_dataset(val_pairs)

        for inputs, targets in train_ds.take(1):
            print(f'inputs["encoder_inputs"].shape: {inputs["encoder_inputs"].shape}')
            print(f'inputs["decoder_inputs"].shape: {inputs["decoder_inputs"].shape}')
            print(f"targets.shape: {targets.shape}")

        return train_ds, val_ds
