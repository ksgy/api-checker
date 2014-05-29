API Checker plugin for Sublime Text
===================================

A plugin to check if an API or a site is up and running. You can make HTTP calls similar as in [SublimeHttpRequester](https://github.com/braindamageinc/SublimeHttpRequester)

Inspiration came from [sublimetext-LondonUnderground](https://github.com/sabarasaba/sublimetext-LondonUnderground) :)

![API Checker](http://i.imgur.com/OsW35op.png)

Example configuration: (api-checker.sublime-settings)

	{
		"debug": true,
		"timeout": 30,
		"up_label": "✓",
		"dn_label": "✕",
		"detailed_error": true,
		"urls": [
			{
				"title": "google",
				"request_type": "GET",
				"request_body": [
				],
				"url": "http://google.com",
			},
			{
				"title": "non-existent",
				"request_type": "POST",
				"request_body": [
					"Access-Control-Request-Headers: accept",
					"Access-Control-Allow-Origin: *",
					"Content-type: application/x-www-form-urlencoded",

					"POST_BODY:",
					"api_key=test_key&getuser=john"
				],
				"url": "http://some.non-existent.url",
			}
		]
	}

Avaliable options
-----------------

-  __debug__

	Show/hide debug messages. Prints out all request and response messages to console.

-  __timeout__

	How often to make request to URLs (in seconds)

-  __up_label__

	Label to show if the API/site is up and running

-  __dn_label__

	Label to show if the API/site is down

-  __detailed_error__

	Show/hide HTTP error code if site is down (eg.: My API✕ (500))

-  __urls__

	Dictionary of APIs/sites to check

	-  __title__

		Title to show in status bar

	-  __request_type__

		HTTP request type: POST/GET/PUT/DELETE

	-  __request_body__

		Request headers, POST_BODY.

		See [SublimeHttpRequester](https://github.com/braindamageinc/SublimeHttpRequester) for more information

	-  __url__

		URL to request




License
-------

The MIT License (MIT)

Copyright (c) 2014 ksgy
