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
	--name x-moderator-qdrant \
	-h x-moderator-qdrant \
	-e QDRANT__TELEMETRY_DISABLED="true" \
	-p 6333:6333/tcp \
	-v "$(pwd)/config/qdrant.yaml:/qdrant/config/production.yaml" \
	-v "$(pwd)/qdrant:/qdrant/storage" \
	qdrant/qdrant
```


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
	-e QDRANT_HOST="" \
	-e QDRANT_API_KEY="" \
	-u "$(id -u):$(id -g)" \
	-v "$(pwd):/home/xembedtool/" \
	x-embed-tool
```

### Environment Variables

| Name                       | Default                         | Description                                                                            |
|----------------------------|---------------------------------|----------------------------------------------------------------------------------------|
| QDRANT_HOST                | http://x-moderator-qdrant:6333  | Qdrant hostname and port.                                                              |
| QDRANT_API_KEY             |                                 | If required, set the API key to use.                                                   |
