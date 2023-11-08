#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys
import platform
import json
import uuid
import logging
import hashlib
import requests
import traceback

from utils import *
from search_result import SearchResult
from typing import Union, List, Any
from urllib.parse import urlparse
from gpt4all import GPT4All
from qdrant_client import QdrantClient, models

logger = logging.getLogger(__name__)

class Search():

    def __init__(self, qdrant:QdrantClient):
        self.qdrant = qdrant

    def search(self, input:str, max_results:int) -> list[SearchResult]:
        pass


    """
    This function is actually quite slow because it's single-threaded.
    Unlike if this were re-written in Java we could make use of multi-threaded xxhash.
    """
    def _check_hash(self, filename:str, expected_hash:str) -> bool:
        if os.path.isfile(f"{self.model_path}/{filename}"):
            #file_hash = hashlib.md5(open(f"{self.model_path}/{filename}", "rb").read()).hexdigest()
            md5 = hashlib.md5()
            
            with open(f"{self.model_path}/{filename}", "rb") as f:
                while True:
                    buf = f.read(2**18)
                    if not buf:
                        break
                    md5.update(buf)

            file_hash = md5.hexdigest()

            if file_hash == expected_hash:
                return True        
        return False


    def _download_model(self, url:str, filename:str) -> bool:

        logger.info(f"Downloading model ({filename}) from {url} ...")

        retry_count = 0
        
        while retry_count <= 3:
            try:
                response = requests.get(url, stream=True)

                if not response.status_code == 200 and not response.status_code == 304:
                    logger.error(f"Failed to get model list {self.model_downloads}: HTTP Status {response.status_code}")
                    return False
                
                with open(f"{self.model_path}/{filename}", "wb") as f:
                    for chunk in response.iter_content(chunk_size=16 * 1024):
                        f.write(chunk)
                    f.close()

                return True
            except:
                logger.warning(f"Download for model {url} failed, retrying ...")
                retry_count = retry_count + 1
                pass
        
        logger.error(f"Tried downloading model {url} 3-times and failed.")
        return False


    def _load_model_config(self) -> dict:
        try:
            fp = open("config/model.json", 'r')
            content = fp.read()
            fp.close()

            model = json.loads(content)
            filename = model["file"]
            hash = model["hash"]
            url = model["url"]

            valid = False

            # Check the file hash against what was downloaded
            if self.skip_integrity_check == False:
                logger.info(f"Checking model integrity: {filename} ...")
                if self._check_hash(filename, hash):
                    logger.info(f"Verified model integrity: {filename}")
                    valid = True
                else:
                    logger.warning(f"Model integrity check for: {filename} failed. Re-downloading ...")
            else:
                valid = True

            # Check if the file exists, if not download it
            if not os.path.isfile(f"{self.model_path}/{filename}") or not valid:
                success = self._download_model(url, filename)
                if not success:
                    raise Exception(f"Failed to download and save model {filename} from {url} !")

                # Verify hash of the downloaded file
                if self.skip_integrity_check == False:
                    if self._check_hash(filename, hash):
                        valid = True
                else:
                    valid = True

            if not valid:
                raise Exception("valid == False")

            return model

        except:
            logger.error("error parsing config/model.json:")
            traceback.print_exc()
            pass
