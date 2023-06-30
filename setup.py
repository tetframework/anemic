from pathlib import Path

from setuptools import find_packages, setup

here = Path(__file__).parent
README = (here / "README.md").read_text()
CHANGES = (here / "CHANGES.md").read_text()


requires = """
    wired
""".split()

dev_requires = [
    "pytest"
]

setup(
    name="anemic",
    version="0.0.1dev0",
    description="",
    long_description=README + "\n\n" + CHANGES,
    classifiers=[
        "Development Status :: 1 - Planning",
        "Environment :: Console",
        "Framework :: Pyramid",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3 :: Only",
        "Topic :: Internet :: WWW/HTTP :: WSGI",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Application",
        "Topic :: Internet :: WWW/HTTP :: WSGI :: Middleware",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
    ],
    author="Antti Haapala",
    author_email="antti.haapala@interjektio.fi",
    url="http://www.interjektio.fi",
    keywords="web pyramid",
    packages=find_packages(),
    include_package_data=True,
    zip_safe=False,
    test_suite="anemic",
    install_requires=requires,
    extras_require={"dev": dev_requires},
)
