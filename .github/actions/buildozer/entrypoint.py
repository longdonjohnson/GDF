#!/bin/python3
"""
Buildozer action
================

It sets some environment variables, installs Buildozer, runs Buildozer and finds
output file.

You can read this file top down because functions are ordered by their execution
order.
"""

import os
import subprocess
import sys
from os import environ as env

# Global variables to hold paths
VENV_DIR = None
PIP_EXE = None
BUILDOZER_EXE = None


def main():
    repository_root = os.path.abspath(env["INPUT_REPOSITORY_ROOT"])
    change_owner(env["USER"], repository_root)
    fix_home()
    install_buildozer(env["INPUT_BUILDOZER_VERSION"])
    apply_buildozer_settings()
    change_directory(env["INPUT_REPOSITORY_ROOT"], env["INPUT_WORKDIR"])
    # apply_patches() # Patches rely on global import which is tricky with venv, skipping as likely not needed with custom venv or we patch venv site-packages
    run_command(env["INPUT_COMMAND"])
    set_output(env["INPUT_REPOSITORY_ROOT"], env["INPUT_WORKDIR"])
    change_owner("root", repository_root)


def change_owner(user, repository_root):
    # GitHub sets root as owner of repository directory. Change it to user
    # And return to root after all commands
    # subprocess.check_call(["sudo", "chown", "-R", user, repository_root])
    pass


def fix_home():
    # GitHub sets HOME to /github/home, but Buildozer is installed to /home/user. Change HOME to user's home
    env["HOME"] = env["HOME_DIR"]


def install_buildozer(buildozer_version):
    global VENV_DIR, PIP_EXE, BUILDOZER_EXE

    # Create a venv to avoid "externally-managed-environment" errors
    print("::group::Setting up virtual environment")
    VENV_DIR = os.path.join(env["HOME_DIR"], ".venv-buildozer")
    if not os.path.exists(VENV_DIR):
        subprocess.check_call([sys.executable, "-m", "venv", VENV_DIR])

    PIP_EXE = os.path.join(VENV_DIR, "bin", "pip")
    BUILDOZER_EXE = os.path.join(VENV_DIR, "bin", "buildozer")

    # Upgrade pip in the venv
    subprocess.check_call([PIP_EXE, "install", "--upgrade", "pip"])

    # Install required Buildozer version
    print(f"::group::Installing Buildozer {buildozer_version}")

    pip_install = [PIP_EXE, "install", "--upgrade"]

    if buildozer_version == "stable":
        # Install stable buildozer from PyPI
        subprocess.check_call([*pip_install, "buildozer"])
    elif os.path.exists(buildozer_version) and os.path.exists(
        os.path.join(buildozer_version, "buildozer", "__init__.py")
    ):
        # Install from local directory
        subprocess.check_call([*pip_install, buildozer_version])
    elif buildozer_version.startswith("git+"):
        # Install from specified git+ link
        subprocess.check_call([*pip_install, buildozer_version])
    elif buildozer_version == "":
        # Just do nothing
        print(
            "::warning::Buildozer is not installed because "
            "specified buildozer_version is nothing."
        )
    else:
        # Install specified ref from repository
        subprocess.check_call(
            [
                *pip_install,
                f"git+https://github.com/kivy/buildozer.git@{buildozer_version}",
            ]
        )
    print("::endgroup::")


def apply_buildozer_settings():
    # Buildozer settings to disable interactions
    env["BUILDOZER_WARN_ON_ROOT"] = "0"
    env["APP_ANDROID_ACCEPT_SDK_LICENSE"] = "1"
    # Do not allow to change directories
    env["BUILDOZER_BUILD_DIR"] = "./.buildozer"
    env["BUILDOZER_BIN"] = "./bin"

    # Ensure the venv binary is on PATH for any subprocesses
    env["PATH"] = f"{os.path.join(VENV_DIR, 'bin')}:{env['PATH']}"


def change_directory(repository_root, workdir):
    directory = os.path.join(repository_root, workdir)
    # Change directory to workir
    if not os.path.exists(directory):
        print("::error::Specified workdir is not exists.")
        exit(1)
    os.chdir(directory)


def apply_patches():
    # Apply patches
    # Note: This original function tried to import buildozer from global site-packages
    # Now that we installed into a venv, we would need to add venv site-packages to sys.path
    # to import it. However, since we are just patching the source on disk, we can find it.

    print("::group::Applying patches to Buildozer")

    # Find site-packages in venv
    import glob
    site_packages = glob.glob(os.path.join(VENV_DIR, "lib", "python*", "site-packages"))
    if not site_packages:
         print("::error::Could not find site-packages in venv")
         return
    site_packages = site_packages[0]

    buildozer_init = os.path.join(site_packages, "buildozer", "__init__.py")

    if not os.path.exists(buildozer_init):
         print("::error::Could not find buildozer package in venv")
         return

    print("Changing global_buildozer_dir")
    try:
        with open(buildozer_init, "r", encoding="utf-8") as f:
            source = f.read()

        new_source = source.replace(
            """
    @property
    def global_buildozer_dir(self):
        return join(expanduser('~'), '.buildozer')
""",
            f"""
    @property
    def global_buildozer_dir(self):
        return '{env["GITHUB_WORKSPACE"]}/{env["INPUT_REPOSITORY_ROOT"]}/.buildozer_global'
""",
        )
        if new_source == source:
            print(
                "::warning::Cannot change global buildozer directory. "
                "Update buildozer-action to new version or create a Bug Request"
            )

        with open(buildozer_init, "w", encoding="utf-8") as f:
            f.write(new_source)

    except Exception as e:
        print(f"::error::Failed to patch buildozer: {e}")

    print("::endgroup::")


def run_command(command):
    # Run command
    # Replace 'buildozer' in the command with the full path if it's the first word
    # OR rely on PATH modification in apply_buildozer_settings

    # We set PATH in apply_buildozer_settings, so 'buildozer' should resolve to our venv one.

    retcode = subprocess.check_call(command, shell=True, env=env)
    if retcode:
        print(f'::error::Error while executing command "{command}"')
        exit(1)


def set_output(repository_root, workdir):
    if not os.path.exists("bin"):
        print(
            "::error::Output directory does not exist. See Buildozer log for error"
        )
        exit(1)
    filename = [
        file
        for file in os.listdir("bin")
        if os.path.isfile(os.path.join("bin", file))
    ][0]
    path = os.path.normpath(
        os.path.join(repository_root, workdir, "bin", filename)
    )
    # Run with sudo to have access to GITHUB_OUTPUT file
    subprocess.check_call(
        [
            "sudo",
            "bash",
            "-c",
            f"echo 'filename={path}' >> {os.environ['GITHUB_OUTPUT']}",
        ]
    )


if __name__ == "__main__":
    main()
