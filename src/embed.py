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
from typing import Union, List, Any
from urllib.parse import urlparse
from gpt4all import GPT4All
from qdrant_client import QdrantClient, models

logger = logging.getLogger(__name__)

class Embed():

    def __init__(self):

        self.qdrant_url = os.getenv("QDRANT_URL", "http://x-moderator-qdrant:6333")
        self.qdrant_api_key = os.getenv("QDRANT_API_KEY", None)
        self.qdrant_collection = os.getenv("QDRANT_COLLECTION", "x-moderator-vectors")
        self.skip_integrity_check = os.getenv("SKIP_INTEGRITY_CHECK", False)
        self.recreate_collection = os.getenv("RECREATE_COLLECTION", False)
        
        threads = os.getenv("THREADS", 0)
        device = os.getenv("DEVICE", "cpu")
        self.model_path = os.getenv("MODEL_PATH", "./model/")

        # Load model config
        self.model_config = self._load_model_config()
        logger.debug(f"Model config: {self.model_config}")

        # Load embedding model
        logging.getLogger("gpt4all.gpt4all").setLevel(logging.CRITICAL)
        logging.getLogger("gpt4all.pyllmodel").setLevel(logging.CRITICAL)
        self.gpt4all = GPT4All(model_name=self.model_config["file"], model_path=self.model_path, model_type=self.model_config["type"] or None, n_threads=threads, allow_download=False, device=device)
        
        # Connect to qdrant
        qdrant = urlparse(self.qdrant_url)
        self.qdrant = QdrantClient(url=f"{qdrant.scheme}://{qdrant.netloc}", port=qdrant.port, api_key=self.qdrant_api_key)

        if self.recreate_collection == False:
            exists = False
            for collection_tuple in self.qdrant.get_collections():
                for collection in collection_tuple[1]:
                    if collection.name == self.qdrant_collection:
                        exists = True
                        break

            if not exists:
                self.qdrant.create_collection(
                    collection_name=self.qdrant_collection,
                    vectors_config = {
                        "text": models.VectorParams(size=self.model_config["vectors"], distance=models.Distance.COSINE)
                    }
                )
        else:
            self.qdrant.recreate_collection(
                collection_name=self.qdrant_collection,
                vectors_config = {
                    "text": models.VectorParams(size=self.model_config["vectors"], distance=models.Distance.COSINE)
                }
            )

        logger.info(f"Successfully connected to {self.qdrant_url}")

        try:
            # get all embeds from the embed.json config
            fp = open("config/embed.json", 'r')
            content = fp.read()
            fp.close()
            embeds = json.loads(content)
            points = []
            existing_hashes_field_conditions = []

            for embed in embeds:
                text = embed["text"]
                category = "spam"
                weight = 1.0
                action = 3
                notify = False

                if "category" in embed:
                    category = embed["category"]

                if "weight" in embed:
                    weight = embed["weight"]

                if "action" in embed:
                    action = embed["action"]

                if "notify" in embed:
                    notify = embed["notify"]

                notify_msg = ""
                if notify:
                    notify_msg = " and WILL notify moderators"
                
                logger.info(f"Embedding {len(text)} chars as [{category}] with a weight of {weight}, action of {action}{notify_msg}: '{text}'")
                vec = self.gpt4all.model.generate_embedding(text)
                logger.debug(f"Vector({len(vec)}): {vec}")

                # prepare payload aux data
                payload = {
                    "hash": hashlib.sha1(text.encode("utf-8")).hexdigest(),
                    "text": text,
                    "category": category,
                    "weight": weight,
                    "action": action,
                    "notify": notify
                }

                # create data point
                point = models.PointStruct(
                    id=f"{str(uuid.uuid4())}",
                    payload=payload,
                    vector= {
                        "text": vec
                    }
                )

                field_condition = models.FieldCondition(
                    key="hash",
                    match=models.MatchValue(value=payload["hash"]),
                )

                points.append(point)
                existing_hashes_field_conditions.append(field_condition)



            # Delete all existing hashes from the db before inserting new values
            if len(existing_hashes_field_conditions) > 0:
                self.qdrant.delete(
                    collection_name=self.qdrant_collection,
                    points_selector=models.FilterSelector(
                        filter=models.Filter(
                            should=existing_hashes_field_conditions
                        )
                    )
                )

            # upload all our new points to the qdrant collection
            self.qdrant.upsert(
                collection_name=self.qdrant_collection,
                points=points
            )

        except KeyboardInterrupt:
            print("") # get rid of annoying '^C' print
            logger.info(f"Stopping!")
            pass




    def embed(self, text:str) -> List[float]:
        return self.gpt4all.model.generate_embedding(text)


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


if __name__ == '__main__':
    formatter = logging.Formatter(fmt='%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger = logging.getLogger("root")
    root_logger.setLevel(logging.INFO)
    #root_logger.setLevel(logging.DEBUG)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    Embed()
