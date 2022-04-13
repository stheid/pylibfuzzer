import logging
import shutil
from pathlib import Path
from tempfile import TemporaryDirectory
import numpy as np
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
