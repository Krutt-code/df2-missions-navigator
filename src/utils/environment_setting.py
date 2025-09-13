import glob
import os
import shutil
import subprocess
import sys
import venv

if "cursor.AppImage" in os.path.realpath(sys.executable):
    REAL_PY = "/usr/bin/python3.12"  # путь к системному интерпретатору
    if os.path.exists(REAL_PY):
        print("[info] Перезапуск скрипта системным Python:", REAL_PY)
        os.execve(
            REAL_PY, [REAL_PY] + sys.argv, {"PATH": "/usr/bin:/bin", **os.environ}
        )
    else:
        sys.exit("[error] Не смог найти системный python3.12")


# Функция для создания виртуального окружения
def create_virtualenv(venv_dir):
    print("Создаю виртуальное окружение в", venv_dir)
    venv.create(
        venv_dir,
        with_pip=True,
        symlinks=False,
        upgrade_deps=True,  # Python ≥3.10
    )


def command_exists(cmd_name: str) -> bool:
    return shutil.which(cmd_name) is not None


def install_dependencies_with_poetry(venv_python: str) -> bool:
    """Пытается установить зависимости через Poetry в указанное .venv.

    - Привязывает Poetry к интерпретатору из .venv
    - Выполняет `poetry install` (по умолчанию с --no-root)
    - Поддерживает переменные окружения:
      - POETRY_WITH_GROUPS="dev,test" — добавит `--with dev,test`
      - POETRY_NO_ROOT="1" — принудительно добавит `--no-root` (по умолчанию и так True)
    Возвращает True, если установка через Poetry прошла успешно, иначе False.
    """
    if not command_exists("poetry"):
        return False

    print("Найден Poetry. Привязываю интерпретатор и устанавливаю зависимости...")
    try:
        # Привязать Poetry к интерпретатору из .venv
        subprocess.check_call(["poetry", "env", "use", venv_python])

        install_cmd = ["poetry", "install"]

        # Группы зависимостей
        groups_env = os.environ.get("POETRY_WITH_GROUPS")
        if groups_env:
            install_cmd += ["--with", groups_env]

        # По умолчанию не устанавливаем сам проект (package-mode=false в этом проекте)
        no_root_env = os.environ.get("POETRY_NO_ROOT")
        if no_root_env is None or no_root_env not in ("0", "false", "False"):
            install_cmd += ["--no-root"]

        subprocess.check_call(install_cmd)
        print("Зависимости установлены через Poetry.")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"Ошибка установки через Poetry: {e}")
        return False


def setup_environment():
    # Определение пути к виртуальному окружению и его python
    venv_dir = ".venv"
    venv_created = False
    if os.name == "nt":
        # Windows
        venv_python = os.path.join(venv_dir, "Scripts", "python.exe")
        activate_script = os.path.join(venv_dir, "Scripts", "activate.bat")
    else:
        # Unix-системы (Linux, macOS)
        venv_python = os.path.join(venv_dir, "bin", "python")
        activate_script = os.path.join(venv_dir, "bin", "activate")

    # Если виртуальное окружение отсутствует, создаём его
    if not os.path.isdir(venv_dir):
        create_virtualenv(venv_dir)
        venv_created = True
    else:
        print("Виртуальное окружение уже существует.")

    # Обновление pip
    print("Обновляю pip...")
    try:
        subprocess.check_call([venv_python, "-m", "pip", "--version"])
        print("pip найден в виртуальном окружении. Продолжаю обновление.")
        subprocess.check_call([venv_python, "-m", "pip", "install", "--upgrade", "pip"])
    except subprocess.CalledProcessError as e:
        print(f"Ошибка при проверке/обновлении pip: {e}")
        print(
            "Возможно, pip отсутствует или возникла проблема с разрешениями/песочницей."
        )
        print(
            "Пожалуйста, убедитесь, что 'pip' доступен в PATH или что ваша среда не блокирует его выполнение."
        )
        sys.exit(1)  # Выходим, так как pip не может быть обновлен/найден

    # Установка зависимостей: сначала пытаемся через Poetry, затем fallback на requirements.txt
    used_poetry = False
    if os.path.exists("pyproject.toml"):
        print(
            "Обнаружен pyproject.toml. Пытаюсь установить зависимости через Poetry..."
        )
        used_poetry = install_dependencies_with_poetry(venv_python)
        if not used_poetry:
            print(
                "Poetry недоступен или произошла ошибка. Перехожу к установке через requirements.txt, если он есть."
            )

    requirements_file = "requirements.txt"
    if not used_poetry and os.path.exists(requirements_file):
        print("Устанавливаю зависимости из", requirements_file)
        subprocess.check_call(
            [venv_python, "-m", "pip", "install", "-r", requirements_file]
        )
    else:
        if not used_poetry:
            print(
                f"Файл {requirements_file} не найден, установка зависимостей пропущена."
            )

    # Обработка файлов с расширением .example
    example_files = glob.glob("*.example") + glob.glob(".*.example")
    if example_files:
        print("Проверяю файлы с расширением .example...")
        for example_path in example_files:
            # Имя целевого файла – имя без расширения .example
            target_path = example_path.rsplit(".example", 1)[0]
            if not os.path.exists(target_path):
                print(f"Создаю {target_path} из {example_path}")
                shutil.copy(example_path, target_path)
            else:
                print(f"Файл {target_path} уже существует, пропускаю.")
    else:
        print("Файлы с расширением .example не найдены.")

    print("Настройка окружения завершена.")
    return venv_created


if __name__ == "__main__":
    setup_environment()
