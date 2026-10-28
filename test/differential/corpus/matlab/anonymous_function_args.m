square = @(x) x.^2;
affine = @(x, offset) 3 .* x + offset;
compose = @(f, g) @(x) f(g(x));
values = arrayfun(@(item) item + 1, 1:4);
