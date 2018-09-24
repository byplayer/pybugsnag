repo = pybugsnag
base_command = pytest
coverage = --cov-config setup.cfg --cov=$(repo)
with_report = --cov-report html
term_report = --cov-report term
xml_report = --cov-report xml
reports = $(html_report) $(term_report) $(xml_report)

all: test_all

test_all:
	$(base_command) $(coverage) $(reports) -s --pyargs $(repo)


.PHONY: test_all