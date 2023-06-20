 
# Email-driven process automation

This collection of scripts allow watching for emails in a specific account and
dispatching specific scripts to be run based on sender or subject; it is primarily
meant to be used as automated evidence collection for TugboatLogic.

## Usage

```
PYTHONPATH=.  python3 mailreader.py --mailbox example@domain.com
```

It is also possible to pass `--vault` with the name of a KV mountpoint for HashiCorp Vault as a place to retrieve the credentials from. In this case, you also need to set the following environment variable to point to your Vault instance:

  - `VAULT_ADDR`: Address to the vault server, if necessary
  - `VAULT_TOKEN`: The token to use to authenticate to Vault

Take care of *export* these should they also be needed to authenticate future calls to Vault for credentials (such as for automated evidence collection).

## Dispatching rules

Edit `rules.yaml` according to what you want to happen.

Format is relatively simple; the top-level group `rules:` is split in two different
categories: `senders`, and `subjects`; which are dictionaries of jobs to run per sender
or per email subject, matching exactly.

```
rules:
  senders:
    Veeam@example.com:
      - type: script
        script: jobs/backup_report_evidence.py
  subjects: []
```

In the above (the original case); the script `backup_report_evidence.py` will be run for
every email from `Veeam@example.com`.

```
evidence_collectors:
  - type: tugboatlogic
    id: 34059
    vault: some/kv/mountpoint
    username: myusername
    password: somesecretpassword
    api_key: deadbeefdeadbeefcafecafe
rules:
  senders:
    Veeam@example.com:
      - type: script
        script: jobs/backup_report_evidence.py
        parameters:
          "--date": "received"
      - type: evidence
        collector: 34059
  subjects:
    Employment Dates Report:
      - type: script
        script: jobs/upload_edr.py
```

In this case, same as above, but also whenever an email with the subject "Employment Dates Report"
is encountered, the associated script will be run.

Furthermore; the script will be called with the specific parameters described under parameters:.

Finally, another task will be run to call APIs via the evidence collectors to upload the email as PDF to the relevant endpoint.

Scripts run this way should expect contents of the email as standard input, and may choose to use
the email subject passed as a first argument to the script.


### Rule types

#### script

Runs a script. Expects the additional key `script` for its path.

Optionally, you can add another field `parameters` which should be a dictionary of arguments to
pass to the script -- the key is an actual switch (ie. `--name`, etc.) and the value will be evaluated
as a property of the EmailMessage object being processed (see code).

#### evidence

`collector`: (required) ID of the evidence collector (see below).

#### noop

Does nothing.


### Evidence collectors

An additional section may be added to the rules file to simplify evidence collection.

For now, only the `tugboatlogic` collector exists.

```
evidence_collectors:
  - id: 30042
    type: tugboatlogic
    vault: external/onetrust/backup-reports
```

This is a top-level block, same level as `rules`. It defines evidence collectors, places to make API calls where to save the contents of an EmailMessage in PDF form.

Each collector must have at least `type` and `id` to differentiate from others; the `id` may be implementation-specific: it is possible the type of value to set for the ID may mean something to the collector API to begin with: for example; `id` for TugboatLogic evidence collection is the actual ID of the collection API endpoint.

Should this be used for a different kind of API, the implementation may decide to care or not about what the actual ID here is.


#### tugboatlogic

  - `type`: (required) Type of evidence collector.
  - `id`: (required) ID of the evidence collector. This should be the last part of the evidence URL on TugBoatLogic (the number)
  - `vault`: (optional) Retrieve credentials from this HashiCorp Vault KV mountpoint
  - `username`: (optional, if vault not set) Username for API calls
  - `password`: (optional, if vault not set) Password for API calls
  - `api_key`: (optional, if vault not set) API key for API calls
