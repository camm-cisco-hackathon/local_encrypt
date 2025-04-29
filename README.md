# local_encrypt

**WARNING**
Directories must be named English

# Python 가상환경(`env`) 생성 및 활용 가이드

다음은 프로젝트 폴더 내에 `env`라는 이름의 가상환경을 만들고, 활성화·비활성화하며, `requirements.txt`의 패키지를 설치하는 일련의 절차입니다.

---

## 1. 가상환경 생성

```bash
# (프로젝트 루트 디렉터리로 이동)
cd /path/to/your/project

# Python 3 기준으로 'env'라는 가상환경 생성
python3 -m venv env
```

> **Windows** 환경에서는 만약 `python3` 대신 `python` 명령을 사용해야 할 수도 있습니다:
> ```powershell
> python -m venv env
> ```

---

## 2. 가상환경 활성화

### macOS / Linux

```bash
source env/bin/activate
```

### Windows (PowerShell)

```powershell
.\env\Scripts\Activate.ps1
```

### Windows (CMD)

```cmd
env\Scripts\activate.bat
```

> 활성화 성공 시 쉘 프롬프트 앞에 `(env)`가 붙습니다.

---

## 3. pip 최신화

가상환경 내 `pip`를 최신 버전으로 업그레이드합니다.

```bash
pip install --upgrade pip
```

---

## 4. 패키지 설치

프로젝트 루트에 `requirements.txt` 파일이 있을 때, 다음 명령으로 일괄 설치합니다:

```bash
pip install -r requirements.txt
```

- 설치 완료 후 `pip list` 명령으로 설치된 패키지 목록을 확인할 수 있습니다.

---

## 5. 스크립트 실행

가상환경이 활성화된 상태에서 Python 스크립트를 실행합니다:

```bash
python main.py
```

- 일부 시스템에서는 `python3 main.py`를 사용하기도 합니다.

---

## 6. 가상환경 비활성화

작업이 끝나면 아래 명령으로 빠져나옵니다:

```bash
deactivate
```

> 다시 `(env)` 프롬프트가 사라지면 비활성화된 상태입니다.

---

## 7. 추가 팁

- **.gitignore 설정**  
  ```gitignore
  # venv 폴더 제외
  /env/
  ```
- **자동화 스크립트**  
  `setup_env.sh` 파일을 만들어 두면 간편합니다:
  ```bash
  #!/usr/bin/env bash
  python3 -m venv env
  source env/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
  echo "✅ 가상환경(env) 설정 및 패키지 설치 완료!"
  ```
  ```bash
  chmod +x setup_env.sh
  ./setup_env.sh
  ```
