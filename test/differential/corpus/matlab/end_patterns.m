function result = end_patterns(varargin)
switch nargin
    case 0
        result = [];
    case 1
        result = varargin{1};
    otherwise
        result = varargin{1:end};
end
for index = 1:numel(result)
    if isempty(result{index})
        continue
    end
end
end
