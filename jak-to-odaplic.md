To clean up:

```
multipass delete --purge stockfish-test
```

New VM: 

```
multipass networks
multipass set local.bridged-network=en0
multipass delete --purge stockfish-test
multipass launch 24.04 --name stockfish-test --memory 2G --disk 10G --network bridged
multipass list
```

Select 2nd IPv4 and use it in curl command

In VM:
```
multipass shell stockfish-test

export YOUR_USER=Akej24
export YOUR_REPO=chess-web

curl -fsSL -o install.sh https://raw.githubusercontent.com/$YOUR_USER/$YOUR_REPO/main/install.sh
sudo REPO_URL=https://github.com/$YOUR_USER/$YOUR_REPO.git bash install.sh
```

In RPI8AI (password=pass):

```
user@192.168.88.39
curl -G http://<2nd_ipV4>:8000/api/fen --data-urlencode "fen=rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
```