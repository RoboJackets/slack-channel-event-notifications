default: local

clean:
	rm -rf _bundle
	rm -rf _bundle.zip

env.json:
	echo '{"ApiLambda": {"SLACK_SIGNING_SECRET": "", "SLACK_API_TOKEN": "", "SLACK_NOTIFY_CHANNEL": ""}}' > env.json

_bundle.zip: clean
	poetry bundle venv _bundle/ --clear --platform manylinux2014_arm64 --python /home/kristaps/miniconda3/bin/python3.13
	cd _bundle/lib/python3.13/site-packages/; zip -r ../../../../_bundle.zip .

local: _bundle.zip env.json
	sam local start-api --region us-east-1 --profile gatech_771971951923_Shibboleth-fulladmin_credfile --docker-network host --env-vars env.json
