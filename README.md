# Table of contents
* [Introduction](#introduction)
    * [AbSeq](#abseq)
       * [About](#about)
* [Supported platforms](#supported-platforms)
* [External dependencies](#external-dependencies)
    * [The easy way](#the-easy-way)
    * [The hard way](#the-hard-way)
        * [Mandatory dependencies](#mandatory-dependencies)
        * [Optional dependencies](#optional-dependencies)
        * [IgBLAST configuration](#igblast-configuration)
* [Installation](#installation)
    * [The recommended way](#the-recommended-way)
    * [From source](#from-source)
* [Usage](#usage)
    * [Help](#help)
    * [YAML](#yaml)
    * [Gotchas](#gotchas)

# Introduction

## AbSeq
`abseqPy` is a quality control pipeline for high throughput antibody sequencing.

This program is intended to be used in conjunction with [`abseqR`](https://github.com/malhamdoosh/abseqR),
a visualizer for the data generated by `abseqPy`. Although `abseqPy` works fine _without_ `abseqR`, it is
highly recommended that users also install the R counterpart to collate and visualize all the results
in a HTML document.

> AbSeq is the collective noun for `abseqPy` and `abseqR`

### About
* `AbSeq` is developed by Monther Alhamdoosh and JiaHong Fong
* For comments and suggestions, email m.hamdoosh \<at\> gmail \<dot\> com



# Supported platforms

`abseqPy` works on most Linux distros, macOS, and Windows.

Some features are *disabled* when running in *Windows* due to software incompatibility, they are:

* Upstream clustering when `--task 5utr`
* Sequence logo generation in `--task diversity`

> `abseqPy` runs on Python 2.7 &mdash; fret not, Python 3.6 support is under way.


# External dependencies

`abseqPy` depends on a few external software to work and they should be properly
installed and configured before running `abseqPy`

## The easy way

This is the __recommended installation process__.

A python script is available [here](install.py) which downloads and installs all the necessary external dependencies.

> **Access to the internet is required for the script to download files**.


The python installer script expects these tools to be present on your `PATH`:

* [perl](https://www.perl.org/get.html)
* [git](https://git-scm.com/)
* [python](https://www.python.org)
* [Java JRE](http://www.oracle.com/technetwork/java/javase/downloads/jre8-downloads-2133155.html) version 1.6 or higher
* [C/C++ compilers](https://gcc.gnu.org/) (not required for Windows)
* [make](https://en.wikipedia.org/wiki/Make_(software)) (not required for Windows)
* [CMake](https://cmake.org/) (not required for Windows)

then, installing external dependencies into a folder named `~/.local/abseq` is as easy as

```bash
$ mkdir -p ~/.local/abseq
$ python install.py ~/.local/abseq
```

> This script does _not_ install `abseqPy` itself, only its external dependencies.

The script works with Python 2 and 3, and `~/.local/abseq` can be replaced with any directory.
However:
* this directory will be there to stay, so choose wisely
* the script will dump more than just binaries in this directory, it will contain databases and internal files

The script will also remind users to update their environment variables if the installation process
succeeded. Likewise, if the directory was moved (in the future), these environment variables need to be updated.


## The hard way

This section is for when one:

1. finds that the installation script failed
2. is feeling adventurous

The installation script mentioned above automates the following installation procedure:

#### Mandatory dependencies 
* [Clustal Omega](http://www.clustal.org/omega/) v1.2.1 or higher
    - Download and extract the tarball or download and use the pre-compiled binaries
* [FastQC](https://www.bioinformatics.babraham.ac.uk/projects/download.html#fastqc) v0.11.5 or higher
    - Download and extract the binaries
* [leeHom](https://github.com/grenaud/leeHom) latest GitHub version
    - Only one of `leeHom`, [`FLASH`, `PEAR`](#optional-dependencies) is required.
    - This is the default merger used by AbSeq on non Windows machines. AbSeq switches to [FLASH](#optional-dependencies) as
    the default merger if it detects Windows; Windows users might find it easier to just download the pre-built
    `FLASH` binary.
    - Follow the installation guide in their README , leeHom uses `CMake` and `make` as their build tool.
* [IgBLAST](ftp://ftp.ncbi.nih.gov/blast/executables/igblast/release/) v1.7
    - Make sure to follow **_every_** step detailed in the [guide](https://ncbi.github.io/igblast/cook/How-to-set-up.html)
    - **_Important_**: The environment variable `$IGDATA` must be exported, as stated in the guide.
* [Ghostscript](https://www.ghostscript.com/download/gsdnld.html) v9.22 or higher
    - Download and follow the instructions to install [here](https://www.ghostscript.com/doc/9.22/Install.htm)

#### Optional dependencies
* [FLASH](https://sourceforge.net/projects/flashpage/files/) v1.2.11 or higher
    - Required if `leeHom` and `PEAR` is not installed
    - Download, extract, `make` or download the pre-built binary
* [PEAR](https://www.h-its.org/downloads/pear-academic/#release) any version
    - Required if `FLASH` and `leeHom` is not installed


### IgBLAST configuration

A final note, if the installation script was not used, be sure to set the environment variable `IGBLASTDB` to
the path where the germline V, D, and J gene sequences are. (i.e. the directory where `my_seq_file` lives in the
example in IgBLAST's [how to setup](https://ncbi.github.io/igblast/cook/How-to-set-up.html))

If `IGBLASTDB` is not configured, `abseqPy` will require the `-d` or `--database` flag (see `abseq -h`)
to be specified with the same directory as `IGBLASTDB` would have had. Otherwise, it is implied that the database
is found in `IGBLASTDB`.

# Installation

This section demonstrates how to install `abseqPy`.

## The recommended way

```bash
pip install abseqPy
```

## From source
```bash
$ git clone <abseq url>
$ cd abseqPy
$ pip install .
```

`abseq` should now be available on your command line.

> installing `abseqPy` also installs other python packages, consider using a python virtual environment to prevent 
overriding existing packages. See [virtualenv](https://packaging.python.org/guides/installing-using-pip-and-virtualenv/)
or [conda](https://conda.io/docs/user-guide/tasks/manage-environments.html).


# Usage
## Help

Invoking `abseq -h` in the command line will display the arguments `AbSeq` uses.


## YAML

Besides calling `abseq` with command line arguments, `abseq` also supports `-y <file>` or `--yaml <file>` that
reads off arguments defined within the provided `file`.

#### Example
Assuming a file named `example.yml` has the following content:

```yaml
defaults:
    task: all
    outdir: results
    threads: 7
    bitscore: 350
    alignlen: 260
    sstart: 1-3
---
name: PCR1
file1: fastq/PCR1_ACGT_L001_R1.fastq.gz
file2: fastq/PCR1_ACGT_L001_R2.fastq.gz
---
name: PCR2
file1: fastq/PCR2_ACGT_L001_R1.fastq.gz
file2: fastq/PCR2_ACGT_L001_R2.fastq.gz
---
name: PCR3
file1: fastq/PCR3_ACGT_L001_R1.fastq.gz
file2: fastq/PCR3_ACGT_L001_R2.fastq.gz
bitscore: 300
task: abundance
detailedComposition: ~
```

then executing `abseq -y example.yml` is equivalent to running 3 simultaneous instances of
`abseq` with the arguments in the `defaults` field applied to each sample (PCR1, PCR2, PCR3):

```bash
$ abseq --task all --outdir results --threads 7 --bitscore 350 --alignlen 260 --sstart 1-3 \
>   --name PCR1 --file1 fastq/PCR1_ACGT_L001_R1.fastq.gz --file2 fastq/PCR1_ACGT_L001_R2.fastq.gz
$ abseq --task all --outdir results --threads 7 --bitscore 350 --alignlen 260 --sstart 1-3 \
>   --name PCR2 --file1 fastq/PCR2_ACGT_L001_R1.fastq.gz --file2 fastq/PCR2_ACGT_L001_R2.fastq.gz
$ abseq --task abundance --outdir results --threads 7 --bitscore 300 --alignlen 260 --sstart 1-3 \
>   --name PCR3 --detailedComposition --file1 fastq/PCR3_ACGT_L001_R1.fastq.gz --file2 fastq/PCR3_ACGT_L001_R2.fastq.gz
```

> The sample PCR3 *overrides* the `bitscore` and `task` argument with `300` and `abundance` and enables the `--detailedComposition` flag.

## Gotchas

1. In the above example, specifying `threads: 7` in the `defaults` key of `example.yml` will run _each_ sample with
7 threads, that is, `abseqPy` will be running with 7 * `number of samples` total threads.
