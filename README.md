# x-embed-tool

A tool for generating text embeddings for X-Moderator in a qdrant vector-database.

### Config

#### embed.json

The following table represents valid parameters to set per entry in the embed.json file.
| Name              | Type    | Default                | Description                                                                            |
|-------------------|---------|------------------------|----------------------------------------------------------------------------------------|
| `text`            | string  |                        | Text value to embed.                                                                   |
| `category`        | string  | "spam"                 | The category to classify this embedding under.                                         |
| `weight`          | float   | 1.0                    | How heavily this individual embedding should be weighed.                               |
| `action`          | int     | 3                      | Action to be taken when the prompt exceeds the threshold.                              |
| `notify`          | boolean | false                  | Notify/mention moderators when the prompt exceeds the threshold.                       |

#### Valid Actions

- `0` (ignore) - Do nothing. This does NOT increment violation count.
- `1` (log) - Only increment the violation count. This WILL increment violation count on the user.
- `2` (hide) - Hide the post (requires X API access). This WILL increment violation count on the user.


### Usage

#### Create a network for x-moderator
```sh
docker network create x-moderator
```


#### Create and run a Qdrant DB

See more configuration options here:
- [Qdrant Installation](https://qdrant.tech/documentation/guides/installation/)
- [Qdrant Configuration](https://qdrant.tech/documentation/guides/configuration/)

```sh
# Create directory for datastore volume mount
mkdir -p qdrant/

# Copy default configs
cp config/qdrant.yaml.example config/qdrant.yaml

# Run
docker run -d \
	--net x-moderator \
	--name x-moderator-qdrant \
	-h x-moderator-qdrant \
	-e QDRANT__TELEMETRY_DISABLED="true" \
	-p 6333:6333/tcp \
	-v "$(pwd)/config/qdrant.yaml:/qdrant/config/production.yaml" \
	-v "$(pwd)/qdrant:/qdrant/storage" \
	qdrant/qdrant
```

You may navigate to http://localhost:6333/dashboard#/collections to view the collections via the built-in dashboard.

#### Build Docker Image

First build the Docker image:
```sh
./docker-build.sh
```


#### Run Container

```sh
# Create required directories
mkdir -p model/

# Copy default configs
cp config/model.json.example config/model.json
cp config/embed.json.example config/embed.json

# Run
docker run --rm -it \
	--net x-moderator \
	-e ENV_VAR_1="123" \
	-e ENV_VAR_2="456" \
	-u "$(id -u):$(id -g)" \
	-v "$(pwd):/home/xembedtool/" \
	x-embed-tool
```

### Environment Variables

| Name                       | Default                         | Description                                                                            |
|----------------------------|---------------------------------|----------------------------------------------------------------------------------------|
| QDRANT_URL                 | http://x-moderator-qdrant:6333  | Qdrant url with port.                                                                  |
| QDRANT_API_KEY             |                                 | If required, set the API key to use.                                                   |
| QDRANT_COLLECTION          | x-moderator-vectors             | Collection name (table).                                                               |
| THREADS                    | 0                               | Number of threads to use for generating embeddings. If 0, it will use all available.   |
| DEVICE                     | cpu                             | Device to use for generating embeddings.                                               |
| SKIP_INTEGRITY_CHECK       |                                 | If set to 1, the model integrity check will be skipped.                                |
| RECREATE_COLLECTION        |                                 | If set to 1, the collection will be **deleted** and re-created.                        |
