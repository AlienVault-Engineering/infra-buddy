# infra-buddy

[Build Status](https://travis-ci.org/AlienVault-Engineering/infra-buddy.svg?branch=master) 
## Installation

```bash
pip install infra-buddy
```

## Usage

```bash
Usage: infra-buddy [OPTIONS] COMMAND [ARGS]...

Options:
  --artifact-directory PATH      A directory where a service definition
                                 (service.json) and supporting files can be
                                 found.
  --application TEXT             The application name.
  --role TEXT                    The role name
  --environment TEXT             The environment the deployment should target.
  --configuration-defaults PATH  A json file with a dictionary of the default
                                 values
  --verbose                      Print verbose status messages
  --help                         Show this message and exit.

Commands:
  deploy-cloudformation
  deploy-service
  generate-artifact-manifest
  generate-service-definition
  validate-template
  
```

 ### Examples
 
 1. Generate a service which defines a vpc
 
 ```bash
 infra-buddy  --application demo --role vpc generate-service-definition
 ``` 
 
 2. Deploy a service definition into the 'ci' environment
 
 ```bash
 infra-buddy  --artifact-directory . --environment ci deploy-service
 ``` 
 
 3. Validate a new service definition is and print out the execution plan.
  
  ```bash
  infra-buddy  --artifact-directory . --environment ci validate-template  --service-type foo --service-definition-directory ../foo-template
  ``` 
 
 4. Validate a built in service definition and print out the execution plan.
      
  ```bash
  infra-buddy  --artifact-directory . --environment ci validate-template  --service-type cluster
  ``` 
     