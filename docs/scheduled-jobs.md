# Scheduled jobs

_In the projects generated with `background_jobs: cron`, this page takes the place of [Background jobs](background-jobs.md)._ <!-- copier:template -->

`purge` deletes the expired refresh tokens, single-use tokens and rate limit counters: schedule it once a day. The `remote` image has no `just`, so run the module directly:

```bash
docker compose run --rm backend python -m app.cli.main purge
```

With cron, on the host that runs Compose:

```
0 3 * * * cd /srv/my-api && docker compose run --rm backend python -m app.cli.main purge
```

On Kubernetes, as a CronJob with the backend image and its environment:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: purge
spec:
  schedule: "0 3 * * *"
  concurrencyPolicy: Forbid
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: purge
              image: registry.example.com/my-api:1.0.0
              args: ["python", "-m", "app.cli.main", "purge"]
              envFrom:
                - secretRef:
                    name: my-api
```
