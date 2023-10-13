# portable checker for MATLAB syntax

### usage

You need to build it with

```bash
docker build . --tag=matlab-checker
```

and then run the image with

```bash
docker run -it --init matlab-checker
```
