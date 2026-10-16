"""
The emails package: send emails without making requests wait.

Services depend on the ``EmailSender`` protocol: requests get one that sends
after the response (``BackgroundEmailSender``), delivering through SMTP, or to
the logs during local development.
"""
