import setuptools

setuptools.setup(
    name="dota2-cast-assist",
    version="0.1.0",
    install_requires=[
        "dill==0.3.9",
        "pydantic==2.9.2",
        "chardet==5.2.0",
        "google-cloud-firestore==2.19.0",
        "google-cloud-secret-manager==2.21.0",
    ],
    packages=setuptools.find_packages()
)
