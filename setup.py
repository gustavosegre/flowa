import os
from setuptools import setup
from setuptools.command.install import install
from setuptools.command.develop import develop

ETL_TEMPLATE = """\
name: etl_pipeline

schedule:
  days: All Days
  start: "08:00"
  end: "18:00"
  interval_minutes: 60

max_parallel: 2

steps:

  - name: extract
    run: python scripts/extract.py
    retries: 2
    timeout_seconds: 120

  - name: transform
    run: python scripts/transform.py
    depends_on: extract
    retries: 1
    timeout_seconds: 300

  - name: load
    run: python scripts/load.py
    depends_on: transform
    retries: 2
    timeout_seconds: 120
"""


def _create_pipelines_dir():
    base_dir = os.path.join(os.getcwd(), "flowa-core")
    pipelines_dir = os.path.join(base_dir, "pipelines")
    logs_dir = os.path.join(base_dir, "logs")
    data_dir = os.path.join(base_dir, "data")

    for path, label in [
        (pipelines_dir, "flowa-core/pipelines"),
        (logs_dir, "flowa-core/logs"),
        (data_dir, "flowa-core/data"),
    ]:
        if not os.path.exists(path):
            os.makedirs(path)
            print(f"[flowa] Created {label}/ at {path}")

    etl_path = os.path.join(pipelines_dir, "etl.yaml")
    if not os.path.exists(etl_path):
        with open(etl_path, "w") as f:
            f.write(ETL_TEMPLATE)
        print(f"[flowa] Created template flowa-core/pipelines/etl.yaml")


class PostInstall(install):
    def run(self):
        install.run(self)
        _create_pipelines_dir()


class PostDevelop(develop):
    def run(self):
        develop.run(self)
        _create_pipelines_dir()


setup(
    cmdclass={
        "install": PostInstall,
        "develop": PostDevelop,
    },
)
