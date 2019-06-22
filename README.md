# Usage
## Deploy to AWS
Install the dependencies.

```shell
$ pip3 install -r requirements.txt -t lib
$ pip3 install -r requirements_bs.txt -t .
```

Deploy to AWS using the [Serverless Framework](https://serverless.com) CLI.

```shell
$ sls deploy -v
```