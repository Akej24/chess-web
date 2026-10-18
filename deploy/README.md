# Deploying from GitHub

Everything runs on your own hardware. The VM only makes outbound connections to
GitHub, so you don't need to open any inbound ports for deployment.

How it works:

1. You push code to GitHub.
2. A systemd timer on the VM checks GitHub every 5 minutes (`deploy/update.sh`).
3. If there are new commits, it pulls them, updates dependencies and restarts the
   service. If nothing changed, it does nothing.

| File | Runs on | Purpose |
|------|---------|---------|
| `../install.sh` | the VM | One-time setup: packages, clone, venv, systemd units |
| `update.sh` | the VM | Pull and redeploy when GitHub has new commits |
| `stockfish-web.service` | the VM | Runs `web.py` on port 8000 |
| `stockfish-web-update.service` / `.timer` | the VM | Runs `update.sh` every 5 minutes |
| `proxmox-create-vm.sh` | Proxmox host | Builds the whole VM in one command |

## 1. Put the project on GitHub

```bash
git push -u origin main
```

`.gitignore` already excludes `.venv/` and `stockfish/`. Keep the scripts executable
(`git update-index --chmod=+x install.sh deploy/*.sh`) if your tools ever drop the flag.

## 2. Proxmox: one script on the host

`proxmox-create-vm.sh` downloads and verifies the Ubuntu 24.04 cloud image, builds a
template (first run only), enables snippets, writes the cloud-init file, creates and
starts the VM, and waits until the viewer answers. Run it in the Proxmox web UI's
**Shell** (node, then Shell) or over SSH:

```bash
curl -fsSL -o create-vm.sh https://raw.githubusercontent.com/YOUR_USER/YOUR_REPO/main/deploy/proxmox-create-vm.sh
bash create-vm.sh --repo https://github.com/YOUR_USER/YOUR_REPO.git \
                  --ssh-key "ssh-ed25519 AAAA... you@mac"
```

Your public key is printed by `cat ~/.ssh/id_ed25519.pub` on your own computer. Useful
options: `--ip 192.168.1.50/24 --gw 192.168.1.1` for a fixed address (default is
DHCP), `--name`, `--vmid`, `--cores`, `--memory`, `--disk`, `--storage`, `--bridge`.
Run `bash create-vm.sh --help` for the full list. Running it again creates another VM
and reuses the template. To remove a VM: `qm stop 120; qm destroy 120`.

The VM is attached to the Proxmox bridge (`vmbr0`), so it gets a normal address on
your home network and other devices can reach it directly.

## 3. Any Ubuntu/Debian VM: `install.sh`

```bash
curl -fsSL -o install.sh https://raw.githubusercontent.com/YOUR_USER/YOUR_REPO/main/install.sh
sudo REPO_URL=https://github.com/YOUR_USER/YOUR_REPO.git bash install.sh
```

### Testing on a Mac with Multipass

By default a Multipass VM sits on a private network that only your Mac can reach, so
other devices (a Raspberry Pi, say) get "No route to host". Bridge it to your real
network instead:

```bash
multipass networks                       # note your interface, often en0
multipass set local.bridged-network=en0
multipass launch 24.04 --name stockfish-test --memory 2G --disk 10G --network bridged
multipass list                           # two IPv4 addresses: use the second one
multipass shell stockfish-test
```

Then run the two `install.sh` lines above inside the VM and test from any device on
your network:

```bash
curl -G http://<second_ipv4>:8000/api/fen --data-urlencode "fen=start"
```

If an old VM is in the way: `multipass delete --purge stockfish-test`. If bridging
doesn't work over Wi-Fi, forward a port on the Mac instead:
`socat TCP-LISTEN:8000,fork,reuseaddr TCP:<vm_ip>:8000`, and use the Mac's address.

## Day to day

```bash
git push                                  # deploys within ~5 minutes
sudo systemctl start stockfish-web-update # deploy right now (on the VM)
journalctl -u stockfish-web -f            # app logs
journalctl -u stockfish-web-update        # what the updater did
systemctl list-timers stockfish-web-update.timer
```

## Private repository

The Proxmox script clones over plain HTTPS, so it needs a public repository. For a
private one, run the script anyway (the VM and your SSH key still work; it will report
that the viewer isn't answering, which is expected), then on the VM create a read-only
**deploy key** and add its public half in GitHub (*Repo, Settings, Deploy keys*):

```bash
sudo -u stockfish ssh-keygen -t ed25519 -N "" -f /home/stockfish/.ssh/id_ed25519
sudo cat /home/stockfish/.ssh/id_ed25519.pub
sudo -u stockfish ssh -o StrictHostKeyChecking=accept-new -T git@github.com
```

Copy `install.sh` to the VM with `scp` and run it with the SSH URL:
`sudo REPO_URL=git@github.com:YOU/REPO.git bash install.sh`.

## Security notes

- The updater runs as root and deploys whatever is on your branch. Anyone who can
  push to it controls the VM, so enable 2FA on GitHub and consider branch protection.
- The viewer has no login. Keep port 8000 on your LAN or behind a VPN (WireGuard,
  Tailscale). Don't port-forward it to the internet without a reverse proxy that
  adds HTTPS and authentication.
