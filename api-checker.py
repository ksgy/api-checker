from datetime import datetime
from threading import Timer

import http.client
import sublime
import sublime_plugin
import socket
import types
import threading


def monitorDownloadThread(downloadThread):
	if downloadThread.is_alive():
		msg = downloadThread.getCurrentMessage()
		sublime.status_message(msg)
		sublime.set_timeout(lambda: monitorDownloadThread(downloadThread), 1000)
	else:
		downloadThread.showResultToPresenter()


class APIChecker(sublime_plugin.EventListener):

	_loaded = False

	def on_activated(self, view):
		if not self._loaded:
			self.fetchAPIStatus()

			self._loaded = True
		else:
			if self._debug:
				print("Active, already initiated")

	def load_settings(self):
		settings = sublime.load_settings('api-checker.sublime-settings')
		self._urls = settings.get('urls', [])
		self._debug = settings.get('debug', False)
		self._timeout = settings.get('timeout', 30)

		if self._debug:
			print("APIChecker | Settings: URLs({0}) Debug({1}) | {2}".format(self._urls, self._debug, self.time()))

	def fetchAPIStatus(self):
		if hasattr(self, '_debug') and self._debug:
			print("APIChecker | Getting API status | {0}".format(self.time()))

		self.load_settings()

		for api in self._urls:
			if(self._debug):
				print("REQUEST", api)
			resultsPresenter = ResultsPresenter()
			httpRequester = HttpRequester(resultsPresenter)
			httpRequester.request(api)

		t = Timer(self._timeout, self.fetchAPIStatus)
		t.start()

	def time(self):
		return datetime.now().strftime('%H:%M:%S')

	_STATUS_KEY = "statusapichecker"


class ResultsPresenter():

	_STATUS_KEY = "statusapichecker"

	def __init__(self):
		settings = sublime.load_settings('api-checker.sublime-settings')
		self._up_label = settings.get('up_label', ': UP')
		self._dn_label = settings.get('dn_label', ': DN')
		self._debug = settings.get('debug', False)
		self._timeout = settings.get('timeout', 30)
		self._detailed_error = settings.get('detailed_error', True)


	def updateStatusBar(self, textToDisplay, fileType, url, title):
		try:
			lines = textToDisplay.split('\n')
		except AttributeError:
			lines = textToDisplay

		parseInt = lambda sin: int(''.join([c for c in str(sin).replace(',','.').split('.')[0] if c.isdigit()])) if sum(map(int,[s.isdigit() for s in str(sin)])) and not callable(sin) else None


		detail = ''
		if(self._debug):
			print ("RESPONSE", lines)

		if lines[0] == "Error connecting" :
			if self._detailed_error:
				detail = ' (Error)'
			sublime.active_window().active_view().set_status(self._STATUS_KEY + url, title + self._dn_label + detail)

		elif parseInt(lines[0]) == 200:
			sublime.active_window().active_view().set_status(self._STATUS_KEY + url, title + self._up_label)

		elif parseInt(lines[0]) >= 300 and parseInt(lines[0]) <= 399:
			sublime.active_window().active_view().set_status(self._STATUS_KEY + url, title + self._up_label)

		elif parseInt(lines[0]) == 400:
			if self._detailed_error:
				detail = ' (400)'
			sublime.active_window().active_view().set_status(self._STATUS_KEY + url, title + self._dn_label + detail)

		elif parseInt(lines[0]) == 404:
			if self._detailed_error:
				detail = ' (404)'
			sublime.active_window().active_view().set_status(self._STATUS_KEY + url, title + self._dn_label + detail)

		elif parseInt(lines[0]) == 500:
			if self._detailed_error:
				detail = ' (500)'
			sublime.active_window().active_view().set_status(self._STATUS_KEY + url, title + self._dn_label + detail)





class HttpRequester(threading.Thread):

	REQUEST_TYPE_GET = "GET"
	REQUEST_TYPE_POST = "POST"
	REQUEST_TYPE_DELETE = "DELETE"
	REQUEST_TYPE_PUT = "PUT"

	httpRequestTypes = [REQUEST_TYPE_GET, REQUEST_TYPE_POST, REQUEST_TYPE_PUT, REQUEST_TYPE_DELETE]

	HTTP_URL = "http://"
	HTTPS_URL = "https://"

	httpProtocolTypes = [HTTP_URL, HTTPS_URL]

	HTTP_POST_BODY_START = "POST_BODY:"

	HTTP_PROXY_HEADER = "USE_PROXY"

	HTTPS_SSL_CLIENT_CERT = "CLIENT_SSL_CERT"
	HTTPS_SSL_CLIENT_KEY = "CLIENT_SSL_KEY"

	CONTENT_LENGTH_HEADER = "Content-lenght"

	MAX_BYTES_BUFFER_SIZE = 8192

	FILE_TYPE_HTML = "html"
	FILE_TYPE_JSON = "json"
	FILE_TYPE_XML = "xml"

	HTML_CHARSET_HEADER = "CHARSET"
	htmlCharset = "utf-8"

	httpContentTypes = [FILE_TYPE_HTML, FILE_TYPE_JSON, FILE_TYPE_XML]

	HTML_SHOW_RESULTS_SAME_FILE_HEADER = "SAME_FILE"
	showResultInSameFile = False

	respText = ""
	fileType = ""

	def __init__(self, resultsPresenter):
		self.totalBytesDownloaded = 0
		self.contentLenght = 0
		self.resultsPresenter = resultsPresenter
		threading.Thread.__init__(self)
		settings = sublime.load_settings('api-checker.sublime-settings')
		self._debug = settings.get('debug', False)
		self._timeout = settings.get('timeout', 30)

	def request(self, api):
		self.selection = api['request_type'] + " " + api['url'] + "\n" +"\n".join(api["request_body"])
		self.apititle = api['title']

		self.start()
		sublime.set_timeout(lambda: monitorDownloadThread(self), 1000)


	def run(self):
		DEFAULT_TIMEOUT = 10
		FAKE_CURL_UA = "curl/7.21.0 (i486-pc-linux-gnu) libcurl/7.21.0 OpenSSL/0.9.8o zlib/1.2.3.4 libidn/1.15 libssh2/1.2.6"

		selection = self.selection

		lines = selection.split("\n")

		# trim any whitespaces for all lines and remove lines starting with a pound character
		for idx in range(len(lines) - 1, -1, -1):
			lines[idx] = lines[idx].lstrip()
			lines[idx] = lines[idx].rstrip()
			if (len(lines[idx]) > 0):
				if lines[idx][0] == "#":
					del lines[idx]

		# get request web address and req. type from the first line
		(url, port, request_page, requestType, httpProtocol) = self.extractRequestParams(lines[0])


		if(self._debug):
			print("Requesting...")
			print(requestType, " ", httpProtocol, " HOST ", url, " PORT ", port, " PAGE: ", request_page)

		# get request headers from the lines below the http address
		(extra_headers, requestPOSTBody, proxyURL,  proxyPort, clientSSLCertificateFile,
		 clientSSLKeyFile) = self.extractExtraHeaders(lines)

		headers = {"User-Agent": FAKE_CURL_UA, "Accept": "*/*"}

		for key in extra_headers:
			headers[key] = extra_headers[key]

		# if valid POST body add Content-lenght header
		if len(requestPOSTBody) > 0:
			headers[self.CONTENT_LENGTH_HEADER] = len(requestPOSTBody)
			requestPOSTBody = requestPOSTBody.encode('utf-8')



		if(self._debug):
			for key in headers:
				print("REQ HEADERS ", key, " : ", headers[key])

		respText = ""
		fileType = ""

		useProxy = False
		if len(proxyURL) > 0:
			useProxy = True

		# make http request
		try:
			if not(useProxy):
				if httpProtocol == self.HTTP_URL:
					conn = http.client.HTTPConnection(url, port, timeout=DEFAULT_TIMEOUT)
				else:
					if len(clientSSLCertificateFile) > 0 or len(clientSSLKeyFile) > 0:
						if(self._debug):
							print("Using client SSL certificate: ", clientSSLCertificateFile)
							print("Using client SSL key file: ", clientSSLKeyFile)
						conn = http.client.HTTPSConnection(
							url, port, timeout=DEFAULT_TIMEOUT, cert_file=clientSSLCertificateFile, key_file=clientSSLKeyFile)
					else:
						conn = http.client.HTTPSConnection(url, port, timeout=DEFAULT_TIMEOUT)

				conn.request(requestType, request_page, requestPOSTBody, headers)
			else:
				if(self._debug):
					print("Using proxy: ", proxyURL + ":" + str(proxyPort))
				conn = http.client.HTTPConnection(proxyURL, proxyPort, timeout=DEFAULT_TIMEOUT)
				conn.request(requestType, httpProtocol + url + request_page, requestPOSTBody, headers)

			resp = conn.getresponse()
			(respText, fileType) = self.getParsedResponse(resp)
			conn.close()
		except (socket.error, http.client.HTTPException, socket.timeout) as e:
			respText = "Error connecting"
		except AttributeError as e:
			if(self._debug):
				print(e)
			respText = "HTTPS not supported by your Python version"

		self.respText = respText
		self.fileType = fileType

	def extractHttpRequestType(self, line):
		for type in self.httpRequestTypes:
			if line.find(type) == 0:
				return type

		return ""

	def extractWebAdressPart(self, line):
		webAddress = ""
		for protocol in self.httpProtocolTypes:
			requestPartions = line.partition(protocol)
			if requestPartions[1] == "":
				webAddress = requestPartions[0]
			else:
				webAddress = requestPartions[2]
				return (webAddress, protocol)

		return (webAddress, self.HTTP_URL)

	def extractRequestParams(self, requestLine):
		requestType = self.extractHttpRequestType(requestLine)
		if requestType == "":
			requestType = self.REQUEST_TYPE_GET
		else:
			partition = requestLine.partition(requestType)
			requestLine = partition[2].lstrip()

		# remove http:// or https:// from URL
		(webAddress, protocol) = self.extractWebAdressPart(requestLine)

		request_parts = webAddress.split("/")
		request_page = ""
		if len(request_parts) > 1:
			for idx in range(1, len(request_parts)):
				request_page = request_page + "/" + request_parts[idx]
		else:
			request_page = "/"

		url_parts = request_parts[0].split(":")

		url_idx = 0
		url = url_parts[url_idx]

		if protocol == self.HTTP_URL:
			port = http.client.HTTP_PORT
		else:
			port = http.client.HTTPS_PORT

		if len(url_parts) > url_idx + 1:
			port = int(url_parts[url_idx + 1])


		# convert requested page to utf-8 and replace spaces with +
		# request_page = request_page.encode('utf-8')
		# request_page = request_page.replace(' ', '+')

		return (url, port, request_page, requestType, protocol)

	def getHeaderNameAndValueFromLine(self, line):
		readingPOSTBody = False

		line = line.lstrip()
		line = line.rstrip()

		if line == self.HTTP_POST_BODY_START:
			readingPOSTBody = True
		else:
			header_parts = line.split(":")
			if len(header_parts) == 2:
				header_name = header_parts[0].rstrip()
				header_value = header_parts[1].lstrip()
				return (header_name, header_value, readingPOSTBody)
			else:
				# may be proxy address URL:port
				if len(header_parts) > 2:
					header_name = header_parts[0].rstrip()
					header_value = header_parts[1]
					header_value = header_value.lstrip()
					header_value = header_value.rstrip()
					for idx in range(2, len(header_parts)):
						currentValue = header_parts[idx]
						currentValue = currentValue.lstrip()
						currentValue = currentValue.rstrip()
						header_value = header_value + ":" + currentValue

					return (header_name, header_value, readingPOSTBody)

		return (None, None, readingPOSTBody)

	def extractExtraHeaders(self, headerLines):
		requestPOSTBody = ""
		readingPOSTBody = False
		lastLine = False
		numLines = len(headerLines)

		proxyURL = ""
		proxyPort = 0

		clientSSLCertificateFile = ""
		clientSSLKeyFile = ""

		extra_headers = {}

		if len(headerLines) > 1:
			for i in range(1, numLines):
				lastLine = (i == numLines - 1)
				if not(readingPOSTBody):
					(header_name, header_value, readingPOSTBody) = self.getHeaderNameAndValueFromLine(headerLines[i])
					if header_name is not None:
						if header_name == self.HTTP_PROXY_HEADER:
							(proxyURL, proxyPort) = self.getProxyURLandPort(header_value)
						elif header_name == self.HTTPS_SSL_CLIENT_CERT:
							clientSSLCertificateFile = header_value
						elif header_name == self.HTTPS_SSL_CLIENT_KEY:
							clientSSLKeyFile = header_value
						elif header_name == self.HTML_CHARSET_HEADER:
							self.htmlCharset = header_value
						elif header_name == self.HTML_SHOW_RESULTS_SAME_FILE_HEADER:
							boolDict = {"true": True, "false": False}
							self.showResultInSameFile = boolDict.get(header_value.lower())
						else:
							extra_headers[header_name] = header_value
				else:  # read all following lines as HTTP POST body
					lineBreak = ""
					if not(lastLine):
						lineBreak = "\n"

					requestPOSTBody = requestPOSTBody + headerLines[i] + lineBreak

		return (extra_headers, requestPOSTBody, proxyURL, proxyPort, clientSSLCertificateFile, clientSSLKeyFile)

	def getProxyURLandPort(self, proxyAddress):
		proxyURL = ""
		proxyPort = 0

		proxyParts = proxyAddress.split(":")

		proxyURL = proxyParts[0]

		if len(proxyParts) > 1:
			proxyURL = proxyParts[0]
			for idx in range(1, len(proxyParts) - 1):
				proxyURL = proxyURL + ":" + proxyParts[idx]

			lastIdx = len(proxyParts) - 1
			proxyPort = int(proxyParts[lastIdx])
		else:
			proxyPort = 80

		return (proxyURL, proxyPort)

	def getParsedResponse(self, resp):
		fileType = self.FILE_TYPE_HTML
		resp_status = "%d " % resp.status + resp.reason + "\n"
		respText = resp_status

		for header in resp.getheaders():
			respText += header[0] + ":" + header[1] + "\n"

			# get resp. file type (html, json and xml supported). fallback to html
			if header[0] == "content-type":
				fileType = self.getFileTypeFromContentType(header[1])

		respText += "\n\n\n"

		self.contentLenght = int(resp.getheader("content-length", 0))

		# download a 8KB buffer at a time
		respBody = resp.read(self.MAX_BYTES_BUFFER_SIZE)
		numDownloaded = len(respBody)
		self.totalBytesDownloaded = numDownloaded
		while numDownloaded == self.MAX_BYTES_BUFFER_SIZE:
			data = resp.read(self.MAX_BYTES_BUFFER_SIZE)
			respBody += data
			numDownloaded = len(data)
			self.totalBytesDownloaded += numDownloaded

		respText += respBody.decode(self.htmlCharset, "replace")

		return (respText, fileType)

	def getFileTypeFromContentType(self, contentType):
		fileType = self.FILE_TYPE_HTML
		contentType = contentType.lower()

		if(self._debug):
			print("File type: ", contentType)

		for cType in self.httpContentTypes:
			if cType in contentType:
				fileType = cType

		return fileType

	def getCurrentMessage(self):
		return "Updating API statuses... " # + str(self.totalBytesDownloaded) + " / " + str(self.contentLenght)

	def showResultToPresenter(self):
		self.resultsPresenter.updateStatusBar(self.respText, self.fileType, self.selection, self.apititle)


