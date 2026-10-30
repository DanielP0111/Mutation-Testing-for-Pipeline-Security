# Foreman

## Purpose

Foreman is a build system analyzer that checks that build phases follow
developer-specified permissions.
This helps developers detect [pipeline
poisoning](https://www.paloaltonetworks.com/cyberpedia/poisoned-pipeline-execution-cicd-sec4)
vulnerabilities and attacks before they reach production code.

We apply for the following badges:

- Available: Foreman is publicly available on
  [Zenodo](https://doi.org/10.5281/zenodo.18190621).

- Functional: Foreman is documented, consistent, complete, exercisable.
  - Documented: This readme provides an [inventory](#inventory) of this
    artifact's contents, and both [quick-start](#kicking-the-tires) and
    [detailed](#step-by-step-demo-instructions) instructions for how to use
    Foreman to detect the poisoned test files in the XZ Utils backdoor.
  - Consistent: Foreman is a direct implementation of the associated paper's
    key idea of "development build phase isolation." Foreman also generates the
    paper's main results, successfully detecting the poisoned test files in the
    XZ Utils backdoor.
  - Complete: This artifact includes all necessary components to run Foreman,
    documents how to use them, and provides expected results.
  - Exercisable: This artifact provides scripts for reproducing the paper's
    main result: the successful detection of the two poisoned test files in the
    XZ Utils backdoor.

- Reusable: This artifact provides detailed instructions on how to incorporate
  Foreman into an existing project to specify its build system's behavior and
  permissions, and check for build phase permission violations.

## Inventory

This artifact contains the following:

```txt
.
├── abstract.pdf                      Artifact abstract
├── Build_Code_is_Code.pdf            Pre-print of associated paper
├── demo                              Directory for demo files
│   └── xz-utils_5.6.0.orig.tar.xz    Copy of compromised XZ Utils version
├── demo.def                          Apptainer definition file for demo
├── foreman.py                        Foreman script for reproducing results
├── LICENSE                           License
├── README.md                         Artifact README with usage instructions
└── run-demo.sh                       Helper script for easily running the demo
```

## Provenance

Zenodo link: <https://doi.org/10.5281/zenodo.18190621>

## Setup

Requirements. See the [Usage](#usage) section for instructions on how to
reproduce the paper's main results.

- Hardware: Any x86 machine.

- Operating system: Ubuntu 22+

- Software:
  - [Apptainer 1.4.5](https://apptainer.org/docs/admin/main/installation.html#install-ubuntu-packages)

## Usage

### Demo: Detecting the XZ Utils backdoor

#### Kicking the Tires

1. Change your file system's settings to use the `strictatime` option:

   ```bash
   sudo mount -o remount,strictatime /
   ```

   This reconfigures the file system to record exactly when each file access
   occurs. By default, Linux machines mount their file systems with the
   `relatime` option, which improves performance at the expense of access time
   accuracy. Using `strictatime` to achieve accurately record access times is
   necessary for Foreman's file access analysis to work.

   To undo this change manually, see the [FAQ](#faq). Otherwise, your file
   system will revert to using the `relatime` option the next time you reset
   your machine.

1. Create the Apptainer image from the provided definition file:

   ```bash
   apptainer build -s demo.sif demo.def
   ```

1. Attach to the just-created container:

   ```bash
   apptainer shell -w demo.sif
   ```

1. Run the helper script:

   ```bash
   ./run-demo.sh
   ```

   The last two lines should be similar to the following, with some path
   differences based on where you downloaded Foreman to your machine:

   ```txt
   warning: make accessed demo/xz-5.6.0/tests/files/bad-3-corrupt_lzma2.xz
   warning: make accessed demo/xz-5.6.0/tests/files/good-large_compressed.lzma
   ```

   This means that Foreman successfully identified the poisoned test cases in
   the XZ Utils backdoor.

#### Step-by-step Demo Instructions

These instructions explain how to obtain the above results without using the
`run-demo.sh` helper script.

1. If you did not run the simple instructions above, then you cans skip this
   step. Alternatively, if you have already followed the simple instructions,
   then first delete your old copy of XZ Utils:

   ```bash
   rm -fr demo/xz-5.6.0
   ```

1. Change your file system's settings to use the `strictatime` option:

   ```bash
   sudo mount -o remount,strictatime /
   ```

1. Create the Apptainer image from the provided definition file:

   ```bash
   apptainer build -s demo.sif demo.def
   ```

1. Attach to the just-created container:

   ```bash
   apptainer shell -w demo.sif
   ```

1. By default, the container should mount the current working directory. This
   directory contains a copy of a compromised version of XZ Utils in a
   compressed tarball. Extract it:

   ```bash
   tar xvf demo/xz-utils_5.6.0.orig.tar.xz -C demo/
   ```

   Note that you may be able to download the tarball from
   <https://launchpad.net/ubuntu/+source/xz-utils/5.6.0-0.2> as well, but we
   provide it in this artifact to help ensure our results are reproducible.

1. Set the environment variable `RPM_ARCH` to `x86_64`.

   ```bash
   export RPM_ARCH=x86_64
   ```

   This is to trick the XZ Utils build system into thinking we are on a Red Hat
   system, since the XZ Utils backdoor only injects itself into the XZ build
   system when built on a Red Hat or Debian machine.

1. Create a basic build system specification for XZ Utils 5.6.0 (if copying
   from Markdown, be sure to remove any leading space before the final EOF!):

   ```bash
   cat <<EOF > demo/xz-5.6.0/build_phases.json
   [
     {
       "name": "autogen",
       "commands": [["./autogen.sh"]]
     },
     {
       "name": "configure",
       "commands": [["./configure"]]
     },
     {
       "name": "make",
       "commands": [["make", "-j", "8"]],
       "permissions": {
           "file": {
               "restricted": ["tests/files/"]
           }
       }
     }
   ]
   EOF
   ```

   The above command creates a JSON specification for XZ Utils' build system
   that Foreman can read. The JSON specification consists of a single array
   comprised of objects representing build phases. All commands have a `name`
   and an array of associated `commands` used to run them. The last object in
   the array also contains an array of files and directories that it is
   `restricted` from accessing.

   You can read more about Foreman's JSON specification in its [corresponding
   section](#foremans-json-specification).

1. Run foreman to execute the XZ Utils build system and check for permission
   violations:

   ```bash
   python3.14 foreman.py -C demo/xz-5.6.0/
   ```

1. Print the results to the console:

   ```bash
   cat demo/xz-5.6.0/warnings*
   ```

   The last two lines should be similar to the following, with some path
   differences based on where you downloaded Foreman to your machine:

   ```txt
   warning: make accessed demo/xz-5.6.0/tests/files/bad-3-corrupt_lzma2.xz
   warning: make accessed demo/xz-5.6.0/tests/files/good-large_compressed.lzma
   ```

   This means that Foreman successfully identified the poisoned test cases in
   the XZ Utils backdoor.

### Using Foreman to analyze other projects

The general "flow" to incorporating Foreman into other projects is as follows:

1. Download Foreman from [Zenodo](https://doi.org/10.5281/zenodo.18190621) and
   extract it. The default extracted directory name is `artifact/`, and the
   following steps assume this directory is available.

1. Download a project whose build system you would like to analyze with
   Foreman. For example, let's download [GNU
   bc](https://www.gnu.org/software/bc/):

   ```bash
   wget https://mirrors.ocf.berkeley.edu/gnu/bc/bc-1.08.2.tar.gz
   tar xvf bc-1.08.2.tar.gz
   ```

1. Create a `build_phases.json` file specifying the project's build steps and
   their permissions. For instance, you could use the following command to
   create a specification with the commands to run bc's configure and compile
   phases, restricting the compile phase from accessing files in the `Test/`
   directory (if copying from Markdown, be sure to remove any leading space
   before the final EOF!):

   ```bash
   cat <<EOF > bc-1.08.2/build_phases.json
   [
     {
       "name": "configure",
       "commands": [["./configure"]]
     },
     {
       "name": "compile",
       "commands": [["make"]],
       "permissions": {
           "file": {
               "restricted": ["Test/"]
           }
       }
     }
   ]
   EOF
   ```

   For more information on the `build_phases.json` file, see its
   [specification](#foremans-json-specification).

1. Run foreman, passing the project directory path to the `-C` argument.

   ```bash
   python3.14 artifact/foreman.py -C bc-1.08.2/
   ```

   This will run BC's configure and compile phases with their specified
   commands (`./configure` and `make`, respectively), and check whether the
   compile phase accesses any files or directories in its `restricted` list.
   Any accesses to restricted files will be logged to a `txt` file whose name
   begins with `warnings` and ends with an ISO time-stamp (e.g.,
   `bc-1.08.2/warnings-2026-04-15-09-00-00.txt`). In this case the warnings
   file should be empty.

## Reference

These subsections are inessential for running the demo, but provide a richer
understanding of how Foreman works, and help prepare users incorporate Foreman
into their own projects.

### Foreman's JSON Specification

Foreman users must specify build phase commands and permissions in a file
called `build_phases.json`. Here is an example, with an explanation afterward:

```json
[
  {
    "name": "configure",
    "commands": [["./configure"]]
  },
  {
    "name": "compile",
    "commands": [["make"]]
  }
]
```

This specifies a build system with a configure phase which runs with the single
command `./configure`, and a compile phase which runs with the single command
`make`.

You can add more strings to a `commands` array element to specify command
arguments and flags; for example, here's how to specify to run `make` with 8
simultaneous jobs with the `-j` flag:

```json
[
  {
    "name": "configure",
    "commands": [["./configure"]]
  },
  {
    "name": "compile",
    "commands": [["make", "-j", "8"]]
  }
]
```

You can specify multiple commands by adding more entries to the `commands`
array. For instance, to run `strace` before `make`:

```json
[
  {
    "name": "configure",
    "commands": [["./configure"]]
  },
  {
    "name": "compile",
    "commands": [["strace"], ["make", "-j", "8"]]
  }
]
```

After specifying a phase's commands, you can then specify the files it has
permission to access in the `permissions` field; for instance, to restrict the
compile phase from accessing the files `tests/test.1` and `tests/test.2`:

```json
[
  {
    "name": "configure",
    "commands": [["./configure"]]
  },
  {
    "name": "compile",
    "commands": [["strace"], ["make", "-j", "8"]],
    "permissions": {
      "file": {
        "restricted": ["tests/test.1", "tests/test.2"]
      }
    }
  }
]
```

You can also put a directory name in a phases `restricted` array to restrict
the phase from accessing any files in that directory. To restrict the compile
phase from accessing any files in the `tests/` directory:

```json
[
  {
    "name": "configure",
    "commands": [["./configure"]]
  },
  {
    "name": "compile",
    "commands": [["strace"], ["make", "-j", "8"]],
    "permissions": {
      "file": {
        "restricted": ["tests/"]
      }
    }
  }
]
```

Sometimes, instead of specifying what files a phase is restricted from
accessing, it's easier to only specify what files a phase is `permitted` to
access. For example, to permit the compile phase to only access files in the
`src/` directory:

```json
[
  {
    "name": "configure",
    "commands": [["./configure"]]
  },
  {
    "name": "compile",
    "commands": [["strace"], ["make", "-j", "8"]],
    "permissions": {
      "file": {
        "permitted": ["src/"]
      }
    }
  }
]
```

You can specify both `restricted` and `permitted` files simultaneously.
Permissions overrule restrictions. For instance, to restrict the configure
phase from accessing any files in the `src/` and `tests/` directories while
permitting the phase to access the directories' `Makefile`s:

```json
[
  {
    "name": "configure",
    "commands": [["./configure"]]
    "permissions": {
      "file": {
        "restricted": ["src/", "tests/"]
        "permitted": ["src/Makefile", "tests/Makefile"]
      }
    }
  },
  {
    "name": "compile",
    "commands": [["strace"], ["make", "-j", "8"]],
    "permissions": {
      "file": {
        "permitted": ["src/"]
      }
    }
  }
]
```

### Foreman's Command Line Interface

To use Foreman to dynamically analyze a project's build system for
vulnerabilities, first create a
[`build_phases.json`](#foremans-json-specification) file in the project's root
directory specifying the project's build phases' commands and permissions.
Then, from within the project's root directory, run Foreman like so (assuming
that Foreman is installed system wide):

```bash
python3.14 foreman
```

By default, Foreman searches the current directory for a `build_phases.json`
file. To run Foreman in a different directory than the current one, use the
`-C` flag:

```bash
python3.14 foreman -C DIRECTORY
```

While dynamically analyzing a project's build phases, Foreman records every
time a build phase accesses a file in a txt file. By default, this file is
named `info-TS.txt`, where TS is an ISO time-stamp. You can change the name of
this file with the `-oi` flag.

When Foreman finishes analyzing a project's build phases, it logs every
detected permission violation to another txt file. By default, this file is
named `warnings-TS`, where TS is an ISO time-stamp. You can change the name of
this file with the `-ow` flag.

For even more information, you can pass the `-h` flag to Foreman to receive
help:

```bash
$ python3.14 foreman.py -h

usage: foreman.py [-h] [-C DIRECTORY] [-oi INFO_FILE] [-ow WARNINGS_FILE]
                  [-pd | --print-directories | --no-print-directories]

options:
  -h, --help            show this help message and exit
  -C, --directory DIRECTORY
                        Change to the given directory before performing any
                        actions.
  -oi, --info-file INFO_FILE
                        Name of file to log file
                        accesses/modifications/changes/creations/deletions to.
                        If not given, a time-stamped filed will be created for
                        logging this info in the current directory.
  -ow, --warnings-file WARNINGS_FILE
                        Name of file to log warnings to. If not given, a time-
                        stamped filed will be created for logging warnings in
                        the current directory.
  -pd, --print-directories, --no-print-directories
                        Whether to log warnings related to directory files.
                        Off by default.
```

## FAQ

- Q: I'm not finding any permission violations!
- A: Ensure that your file system is mounted with the `strictatime` flag. You
  can do this by running the following command (which you may need to execute
  every time you restart your device):

  ```bash
  sudo mount -o remount,strictatime /
  ```

  To revert this change, run:

  ```bash
  sudo mount -o remount,relatime /
  ```
