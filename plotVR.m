function json = plotVR(data, host, port)
% PLOTVR  plot the data to the DataVR-server and relad all attached cardboards.
%   PLOTVR(data) plots data in VR.
%   PLOTVR(data, host) plots data to server at host.
%   PLOTVR(data, host, port) plots data to server at host listening on port.
%
%   In order for this to work a server has to be started using
%   ./startServer.sh.
%   Any connected cardboard then will open a keyboard window on the server,
%   so it is best, this server is started on the desktop machine, this
%   MATLAB is running.
%
%   As an example run
%   plotVR( [1 2 3 4;5 6 7 8] )
%

if nargin <= 2
    port = 2908;
end
if nargin <= 1
   host = 'localhost';
end

host = ['http://' host ':' num2str(port) '/']
    

%%
dc = num2cell(data,2);
lines = cellfun(@convertline, dc, 'Uniform', false);
raw = strjoin(lines, '],[');
json = [ '{"data":[[' raw ']]}' ];

%%
urlread(host,'Post',{'data',char(json)});


function out = convertline(row)
    out = strjoin(cellfun(@num2str,num2cell(row),'Uni',false),',');
end

end
