opbeat-pyramid
--------------


[![CircleCI](https://circleci.com/gh/monokrome/opbeat_pyramid.svg?style=svg)](https://circleci.com/gh/monokrome/opbeat_pyramid)
[![Coverage Status](https://coveralls.io/repos/github/monokrome/opbeat_pyramid/badge.svg?branch=master)](https://coveralls.io/github/monokrome/opbeat_pyramid?branch=master)


Provides middleware for transaction and error reporting  to opbeat from your
Pyramid applications.


### Installation

Installation can be done with easy_install, pip, or whichever package
management tool you prefer:

```
pip install opbeat_pyramid
```


### Usage

Using the module should be simple. You will need to call
`config.include('opbeat_pyramid')` on the configurator for your Pyramid
project. With the standard Pyramid boilerplates, this will be done in the
`main` function within **\__init__.py**.


#### Options

The following options **must be** in your app configuration in order to use
this module:

| Pyramid Setting                  | Environment Variable           | Description                                                                        |
|----------------------------------|--------------------------------|------------------------------------------------------------------------------------|
| opbeat.enabled                 * | OPBEAT_ENABLED                 | True to enable reporting to OpBeat                                                 |
| opbeat.module_name             * | OPBEAT_MODULE_NAME             | The name of your project's module                                                  |
| opbeat.organization_id         * | OPBEAT_ORGANIZATION_ID         | Your opbeat organization ID                                                        |
| opbeat.app_id                  * | OPBEAT_APP_ID                  | Your opbeat app ID                                                                 |
| opbeat.secret_token            * | OPBEAT_SECRET_TOKEN            | Your opbeat secret token                                                           |
| opbeat.unsafe_settings_phrases   | OPBEAT_UNSAFE_SETTINGS_PHRASES | Comma-separated phrases used in setting names that should never be sent to update. |

*NOTE: Settings marked with \* are required*
