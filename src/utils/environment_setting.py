import os
import sys
import venv
import glob
import shutil
import subprocess


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

    # Установка зависимостей из requirements.txt, если файл существует
    requirements_file = "requirements.txt"
    if os.path.exists(requirements_file):
        print("Устанавливаю зависимости из", requirements_file)
        subprocess.check_call(
            [venv_python, "-m", "pip", "install", "-r", requirements_file]
        )

        # Проверяем, есть ли playwright в зависимостях, и устанавливаем браузеры
        with open(requirements_file, "r", encoding="utf-8") as f:
            dependencies = f.read().splitlines()

        if any("playwright" in dep.lower() for dep in dependencies):
            print("Playwright найден в зависимостях. Устанавливаю/обновляю браузеры...")
            try:
                subprocess.check_call([venv_python, "-m", "playwright", "install"])
                print("Браузеры Playwright успешно установлены/обновлены.")
            except subprocess.CalledProcessError as e:
                print(f"Ошибка при установке браузеров Playwright: {e}")
                sys.exit(1)  # Выход, если установка браузеров не удалась
    else:
        print(f"Файл {requirements_file} не найден, установка зависимостей пропущена.")

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
