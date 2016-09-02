opbeat-pyramid
--------------

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

- `opbeat.enabled` should be set to true or opbeat wont be sent anything.
- `opbeat.module_name` should be set to the name of your project's module.
- `opbeat.organization_id` should be set to your opbeat organization ID
- `opbeat.app_id` should be set to your opbeat app ID
- `opbeat.secret_token` should be set to your opbeat secret token

Optional settings:

- `opbeat.unsafe_settings_terms` contains terms used in setting names that should never be sent to update. (default: token,password,passphrase,secret,private,key)

