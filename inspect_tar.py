import tarfile
import urllib.request
import os

url = "https://github.com/ggml-org/llama.cpp/releases/download/b7836/llama-b7836-bin-ubuntu-x64.tar.gz"
print(f"Checking {url}...")
try:
    file_tmp = urllib.request.urlretrieve(url, filename=None)[0]
    with tarfile.open(file_tmp) as tar:
        for member in tar.getmembers():
            print(member.name)
except Exception as e:
    print(e)
