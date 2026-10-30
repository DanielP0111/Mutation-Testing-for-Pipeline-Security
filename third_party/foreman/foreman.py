#!/usr/bin/python3

import argparse
import copy
import dataclasses
import datetime
import json
import os
import pathlib
import subprocess


class Arguments(argparse.Namespace):
    directory: pathlib.Path | None
    info_file: pathlib.Path | None
    warnings_file: pathlib.Path | None
    print_directories: bool | None


def parse_arguments() -> Arguments:
    arguments = Arguments()
    parser = argparse.ArgumentParser()
    parser.add_argument("-C", "--directory", type=pathlib.Path,
                        dest='directory',
                        help="Change to the given directory before performing any actions.")
    parser.add_argument("-oi", "--info-file", type=pathlib.Path,
                        help="Name of file to log file accesses/modifications/changes/creations/deletions to. If not given, a time-stamped filed will be created for logging this info in the current directory.")
    parser.add_argument("-ow", "--warnings-file", type=pathlib.Path,
                        help="Name of file to log warnings to. If not given, a time-stamped filed will be created for logging warnings in the current directory.")
    parser.add_argument("-pd", "--print-directories", action=argparse.BooleanOptionalAction,
                        help="Whether to log warnings related to directory files. Off by default.")
    parser.parse_args(namespace=arguments)
    return arguments



@dataclasses.dataclass
class File_Permissions:
    restricted: list[pathlib.Path]
    permitted: list[pathlib.Path]


@dataclasses.dataclass
class Environment_Variable_Write_Permissions:
    permitted: list[str]
    restricted: list[str]


@dataclasses.dataclass
class Permissions:
    file: File_Permissions | None
    environment_variable_write: Environment_Variable_Write_Permissions | None


Command = list[str]


@dataclasses.dataclass
class Build_Phase:
    name: str
    commands: list[Command]
    permissions: Permissions | None


def load_command(command: list[str]) -> Command:
    if not isinstance(command, list):
        raise ValueError(f"Expected command to be a list[str], got {type(command)}")

    for part in command:
        if not isinstance(part, str):
            raise ValueError(f"Expected command part to be a str, got {type(part)}")

    return command


def load_commands(commands: list[list[str]]) -> list[Command]:
    if not isinstance(commands, list):
        raise ValueError(f"Expected commands to be a list, got {type(commands)}")

    return [load_command(command) for command in commands]


def load_name(name: str) -> str:
    if not isinstance(name, str):
        raise ValueError(f"Expected name to be a str, got {type(name)}")

    return name


def load_path(path: str) -> pathlib.Path:
    if not isinstance(path, str):
        raise ValueError(f"Expected path to be a str, got {type(str)}")
    
    return pathlib.Path(path)


def load_file_permissions(file_permissions: dict) -> File_Permissions:
    if not isinstance(file_permissions, dict):
        raise ValueError(f"Expected file permissions to be a dict, got {type(file_permissions)}")

    restricted = []
    permitted = []

    if "restricted" in file_permissions:
        restricted = [load_path(path_str) for path_str in file_permissions["restricted"]]

    if "permitted" in file_permissions:
        permitted = [load_path(path_str) for path_str in file_permissions["permitted"]]

    return File_Permissions(restricted, permitted)


def load_environment_variable(environment_variable: str) -> str:
    if not isinstance(environment_variable, str):
        raise ValueError(f"Expected environment variable to be a str, got {type(environment_variable)}")
    
    return environment_variable


def load_environment_variable_write_permissions(env_w_permissions: dict) -> Environment_Variable_Write_Permissions:
    if not isinstance(env_w_permissions, dict):
        raise ValueError(f"Expected environment variable write permissions to be a dict, got {type(env_w_permissions)}")

    restricted = []
    permitted = []

    if "restricted" in env_w_permissions:
        restricted = [load_environment_variable(env_str) for env_str in env_w_permissions["restricted"]]

    if "permitted" in env_w_permissions:
        permitted = [load_environment_variable(env_str) for env_str in env_w_permissions["permitted"]]

    return Environment_Variable_Write_Permissions(restricted, permitted)


def load_permissions(permissions: dict) -> Permissions:
    file_: File_Permissions | None = None
    environment_variable_write: Environment_Variable_Write_Permissions | None = None

    if not isinstance(permissions, dict):
        raise ValueError(f"Expected permissions to be a dict, got {type(permissions)}")

    if "file" in permissions:
        file_ = load_file_permissions(permissions["file"])

    if "environment_variable_write" in permissions:
        environment_variable_write = load_environment_variable_write_permissions(
                        permissions["environment_variable_write"])

    return Permissions(file_, environment_variable_write)


def load_build_phases(build_phases_filepath: pathlib.Path) -> list[Build_Phase]:
    data: list = []

    with open(build_phases_filepath) as fp:
        data = json.load(fp)

    if not isinstance(data, list):
        raise ValueError(f"Expected build phases to be a list, got {type(data)}")

    phases: list[Build_Phase] = []
    for datum in data:
        name = load_name(datum["name"])
        commands = load_commands(datum["commands"])
        permissions = load_permissions(datum["permissions"]) if "permissions" in datum else None

        phases.append(Build_Phase(name, commands, permissions))

    return phases


def map_files_in_cwd_to_stats() -> dict[pathlib.Path, int]:
    result = {}
    for file in pathlib.Path.cwd().rglob("*"):
        result[file] = file.stat()
    return result


def is_file_in_any_paths(file: pathlib.Path, paths: list[pathlib.Path]) -> bool:
    file = file.absolute()
    for path in paths:
        path = path.absolute()
        if path.samefile(file):
            return True
        if path.is_dir():
            for otherfile in path.rglob("*"):
                if otherfile.absolute().samefile(file):
                    return True
    return False


@dataclasses.dataclass
class Difference:
    pass


# TODO(Brent): Group created and deleted files separately from modified files.
@dataclasses.dataclass
class File_Stat_Difference(Difference):
    file: pathlib.Path
    accessed: bool
    modified: bool
    changed: bool
    created: bool
    deleted: bool

    def __str__(self):
        if self.created:
            return f'created {self.file}'

        if self.deleted:
            return f'deleted {self.file}'

        verbs = [ verb for verb in ['accessed', 'modified', 'changed' ] if getattr(self, verb) ]
        if len(verbs) == 0:
            return f'no changes to {self.file}'
        elif len(verbs) == 1:
            return f'{verbs[0]} {self.file}'
        elif len(verbs) == 2:
            return f'{verbs[0]} and {verbs[1]} {self.file}'
        elif len(verbs) == 3:
            return f'{verbs[0]}, {verbs[1]}, and {verbs[2]} {self.file}'


@dataclasses.dataclass
class Environment_Variable_Difference(Difference):
    environment_variable: str
    modified: str
    created: str
    deleted: str

    def __str__(self):
        if self.created:
            return f'created {self.environment_variable}'

        if self.deleted:
            return f'deleted {self.environment_variable}'

        if self.modified:
            return f"{self.environment_variable} modified"


def get_environment_variables() -> dict[str, str]:
    # NOTE(Brent): Needs Python 3.14
    os.reload_environ()
    # NOTE(Brent): Since os.environ is a string->string map, and Python strings
    # are immutable, a shallow copy should suffice, but let's use a deep copy
    # to be safe...
    return copy.deepcopy(os.environ)


def run_phases_and_record_differences(phases: list[Build_Phase]) -> list[tuple[Build_Phase, list[Difference]]]:
    phase_and_differences = [ (phase, []) for phase in phases ]
    pre_phase_file_stats = map_files_in_cwd_to_stats()
    pre_phase_env_vars = get_environment_variables()

    for phase, differences in phase_and_differences:
        for command in phase.commands:
            subprocess.run(command)

        post_phase_file_stats = map_files_in_cwd_to_stats()
        post_phase_env_vars = get_environment_variables()

        for file in pre_phase_file_stats:
            if file not in post_phase_file_stats:
                differences.append(File_Stat_Difference(file, False, False,
                                                        False, False, True))
        for file, stats in post_phase_file_stats.items():
            if file not in pre_phase_file_stats:
                differences.append(File_Stat_Difference(file, True, True, True,
                                                        True, False))
            else:
                previous_stats = pre_phase_file_stats[file]
                updated_atime = stats.st_atime > previous_stats.st_atime
                updated_mtime = stats.st_mtime > previous_stats.st_mtime
                updated_ctime = stats.st_ctime > previous_stats.st_ctime
                if updated_atime or updated_mtime or updated_ctime:
                    differences.append(
                            File_Stat_Difference(file,
                                        stats.st_atime > previous_stats.st_atime,
                                        stats.st_mtime > previous_stats.st_mtime,
                                        stats.st_ctime > previous_stats.st_ctime,
                                        False, False))

        for env_var in pre_phase_env_vars:
            if env_var not in post_phase_env_vars:
                differences.append(Environment_Variable_Difference(env_var,
                                                                   modified=False,
                                                                   created=False,
                                                                   deleted=True))
        for env_var in post_phase_env_vars:
            if env_var not in pre_phase_env_vars:
                differences.append(Environment_Variable_Difference(env_var,
                                                                   modified=False,
                                                                   created=True,
                                                                   deleted=False))
            elif pre_phase_env_vars[env_var] != post_phase_env_vars[env_var]:
                differences.append(Environment_Variable_Difference(env_var,
                                                                   modified=True,
                                                                   created=False,
                                                                   deleted=False))

        pre_phase_file_stats = post_phase_file_stats
        pre_phase_env_vars = post_phase_env_vars

    return phase_and_differences


def map_phases_to_violations(phase_and_differences: list[tuple[Build_Phase, list[Difference]]]) -> dict[str, list[Difference]]:
    phase_name_to_violations = { phase.name : [] for phase, _ in phase_and_differences }


    for phase, differences in phase_and_differences:
        violations: list[Difference] = []

        if not phase.permissions:
            continue

        if phase.permissions.file:
            restricted_files = phase.permissions.file.restricted
            permitted_files = phase.permissions.file.permitted

            file_stat_differences = [difference for difference in differences if
                                     isinstance(difference, File_Stat_Difference)]

            if not restricted_files and not permitted_files:
                pass
            elif not restricted_files and permitted_files:
                for file_stat_difference in file_stat_differences:
                    in_permitted = is_file_in_any_paths(file_stat_difference.file,
                                                        permitted_files)
                    if not in_permitted:
                        violations.append(file_stat_difference)
            elif restricted_files and not permitted_files:
                for file_stat_difference in file_stat_differences:
                    in_restricted = is_file_in_any_paths(file_stat_difference.file,
                                                         restricted_files)
                    if in_restricted:
                        violations.append(file_stat_difference)
            else: # restricted_files and permitted_files
                for file_stat_difference in file_stat_differences:
                    # Permissions overrule restrictions
                    in_restricted = is_file_in_any_paths(file_stat_difference.file,
                                                         restricted_files)
                    in_permitted = is_file_in_any_paths(file_stat_difference.file,
                                                        permitted_files)
                    if in_restricted and not in_permitted:
                        violations.append(file_stat_difference)

        if phase.permissions.environment_variable_write:
            restricted_env_vars = phase.permissions.environment_variable_write.restricted
            permitted_env_vars = phase.permissions.environment_variable_write.permitted

            env_var_differences = [difference for difference in differences if
                                   isinstance(difference,
                                              Environment_Variable_Difference)]

            if not restricted_env_vars and not permitted_env_vars:
                pass
            elif not restricted_env_vars and permitted_env_vars:
                for env_var_difference in env_var_differences:
                    in_permitted = env_var_difference.environment_variable in permitted_env_vars
                    if not in_permitted:
                        violations.append(env_var_difference)
            elif restricted_env_vars and not permitted_env_vars:
                for env_var_difference in env_var_differences:
                    in_restricted = env_var_difference.environment_variable in restricted_env_vars
                    if in_restricted:
                        violations.append(env_var_difference)
            else: # restricted_env_vars and permitted_env_vars
                for env_var_difference in env_var_differences:
                    # Permissions overrule restrictions
                    in_restricted = env_var_difference.environment_variable in restricted_env_vars
                    in_permitted = env_var_difference.environment_variable in permitted_env_vars
                    if in_restricted and not in_permitted:
                        violations.append(env_var_difference)

        phase_name_to_violations[phase.name] = violations

    return phase_name_to_violations


def main() -> int:
    now_string = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    original_directory = pathlib.Path.cwd()
    arguments = parse_arguments()
    directory = arguments.directory if arguments.directory is not  None else original_directory
    info_file = arguments.info_file.absolute() if arguments.info_file is not None else pathlib.Path(f'info-{now_string}.txt')
    warnings_file = arguments.warnings_file.absolute() if arguments.warnings_file is not None else pathlib.Path(f'warnings-{now_string}.txt')
    build_phases_filepath = pathlib.Path("build_phases.json")

    os.chdir(directory)

    if not build_phases_filepath.is_file():
        raise ValueError("Could not find build_phases.json")

    phases = load_build_phases(build_phases_filepath)

    phase_and_differences = run_phases_and_record_differences(phases)
    with open(info_file, "w") as fp:
        for phase, differences in phase_and_differences:
            for difference in differences:
                print(f"{phase.name} {difference}", file=fp)

    phase_name_to_violations = map_phases_to_violations(phase_and_differences)
    with open(warnings_file, "w") as fp:
        for phase_name, violations in phase_name_to_violations.items():
            for violation in violations:
                if (isinstance(violation, Environment_Variable_Difference)
                    or  isinstance(violation, File_Stat_Difference)
                        and (violation.file.is_file() or arguments.print_directories)):
                    print(f"warning: {phase_name} {violation}", file=fp)

    os.chdir(original_directory)

    return 0


if __name__ == '__main__':
    exit(main())
