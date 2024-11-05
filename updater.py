import requests
import json
import os
import logging

logging.basicConfig(filename="updater.log",
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    datefmt='%H:%M:%S')
_logger = logging.getLogger("RegRU ddns updater")
_logger.setLevel(logging.INFO)

LAST_IP_FILE_PATH = os.path.join(os.getcwd(), "last_ip.txt")
CONFIG_FILE_PATH = os.path.join(os.getcwd(), "config.json")

REGRU_API_BASE = "https://api.reg.ru/api/regru2/"


def checkIP(config) -> str | None:
    try:
        res = requests.get(config["ip_provider"])
        currentIPAddress = res.text.strip()

        if os.path.exists(LAST_IP_FILE_PATH):
            lastIPAddress = open(LAST_IP_FILE_PATH, "r").read().strip()
        else:
            lastIPAddress = None

        if lastIPAddress == currentIPAddress:
            _logger.info("IP not changed, quitting")
            exit(0)
        else:
            _logger.info("IP changed from %s to %s",
                         lastIPAddress, currentIPAddress)
            open(LAST_IP_FILE_PATH, "w").write(currentIPAddress)
            return currentIPAddress
    except Exception as e:
        if isinstance(e, requests.exceptions.ConnectionError):
            raise Exception("No internet connection, aborting.")
        else:
            raise e


def tryLogin(config):
    res = requests.post(REGRU_API_BASE + "nop",
                        data={
                            "username": config["username"],
                            "password": config["password"],
                            "output_format": "json",
                            "io_encoding": "utf8"
                        })

    res_json = res.json()

    if res_json["result"] != "success":
        raise Exception("Login failed", res.text)
    else:
        _logger.info("Logined as %s", res_json["answer"]["login"])


def checkDomainRights(config):
    domains = []
    for domain in config["domains"]:
        domains.append({"dname": domain["name"]})

    res = requests.post(REGRU_API_BASE + "zone/nop",
                        data={
                            "username": config["username"],
                            "password": config["password"],
                            "output_format": "json",
                            "input_format": "json",
                            "io_encoding": "utf8",
                            "input_data": json.dumps({"domains": domains})
                        })

    res_json = res.json()

    failedDomains = []

    for domain in res_json["answer"]["domains"]:
        if domain["result"] != "success":
            failedDomains.append(domain["dname"])
            _logger.error("Error while processing domain %s: %s (%s)",
                          domain["dname"], domain["error_code"], domain["error_text"])

    if len(failedDomains) > 0:
        _logger.critical("Error while processing %d domain(s)",
                         len(failedDomains))
        exit(1)


def processEdit(config, domain: str, subdomain: str, ip: str):
    inputObj = {
        "domains": [
            {
                "dname": domain
            }
        ],
        "ipaddr": ip,
        "subdomain": subdomain
    }
    res = requests.post(REGRU_API_BASE + "zone/add_alias",
                        data={
                            "username": config["username"],
                            "password": config["password"],
                            "output_format": "json",
                            "input_format": "json",
                            "io_encoding": "utf8",
                            "input_data": json.dumps(inputObj)
                        })
    res_json = res.json()
    res_json = res_json["answer"]["domains"][0]
    if res_json["result"] != "success":
        _logger.error("Error while processing domain %s: %s (%s)",
                      res_json["dname"], res_json["error_code"], res_json["error_text"])
        exit(1)


def processEditZone(config, ip: str):
    for domain in config["domains"]:
        _logger.info("Processing domain %s", domain["name"])
        for record in domain["records"]:
            _logger.info("Processing record %s", record)
            processEdit(config, domain["name"], record, ip)
            _logger.info("Ok")


def main():
    try:
        if not os.path.exists(CONFIG_FILE_PATH):
            _logger.critical("Config file not found in %s", os.getcwd())
            exit(1)

        config = json.load(open(CONFIG_FILE_PATH, "r"))

        if "log_level" in config:
            _logger.setLevel(str(config["log_level"]).upper())

        newIP = checkIP(config)

        tryLogin(config)

        checkDomainRights(config)

        processEditZone(config, newIP)
    except Exception as e:
        _logger.critical(e, exc_info=(_logger.level <= 10))


if __name__ == "__main__":
    main()
