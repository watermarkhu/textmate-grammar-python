classdef test_multiple_inheritance < handle & another_class ...
    & another_class_2
    properties
        Value {mustBeNumeric}
    end
    methods
        function r = roundOff(obj)
            r = round([obj.Value],2);
        end
        function r = multiplyBy(obj,n)
            r = [obj.Value]*n;
        end
    end
end
