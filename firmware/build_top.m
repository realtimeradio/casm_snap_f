function build_top()
    %   Build the top-level design

    design = 'snap_f_12i_4kc.slx';

    if ~isfile(design)
        error(['Design ' design 'does not exist!']);
    end

    disp('Building IP cores')
    build_ip_cores()

    disp(['Building ' design]);
    open_system(design);
    t0=datetime; a = jasper_frontend; system([a ' --jobs 16']); t1=datetime;
    build_duration = t1 - t0
    close_system(design, 0);
