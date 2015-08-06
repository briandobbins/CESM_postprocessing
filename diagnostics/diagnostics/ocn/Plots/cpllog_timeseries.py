""" 
plot module: PM_CPLLOG
plot name:   CPL Surface Heat and Freshwater Flux Budget

classes:
CplLog:            base class
CplLog_timeseries: defines specific NCL list for model timeseries plots
"""

from __future__ import print_function

import sys

if sys.hexversion < 0x02070000:
    print(70 * "*")
    print("ERROR: {0} requires python >= 2.7.x. ".format(sys.argv[0]))
    print("It appears that you are running python {0}".format(
        ".".join(str(x) for x in sys.version_info[0:3])))
    print(70 * "*")
    sys.exit(1)

import glob
import jinja2
import os
import shutil
import subprocess
import traceback


# import the helper utility module
from cesm_utils import cesmEnvLib
from diag_utils import diagUtilsLib

# import the plot baseclass module
from ocn_diags_plot_bc import OceanDiagnosticPlot

class CplLog(OceanDiagnosticPlot):
    """Detailed description of the plot that will show up in help documentation
    """

    def __init__(self):
        super(CplLog, self).__init__()
        self._expectedPlots = ['cplheatbudget','cplfwbudget' ]
        self._labels = ['Heat', 'Freshwater']
        self._linkNames = ['timeseries','table']
        self._name = 'CPL Surface Heat and Freshwater Flux Budget'
        self._shortname = 'CPLLOG'
        self._template_file = 'cpllog_timeseries.tmpl'
        self._ncl = list()
        self._awkError = False
        self._tailError = False

    def check_prerequisites(self, env):
        """list and check specific prequisites for this plot.
        """
        super(CplLog, self).check_prerequisites(env)
        print("  Checking prerequisites for : {0}".format(self.__class__.__name__))

        # chdir into the  working directory
        os.chdir(env['WORKDIR'])

        # parse the cpllog depending on the coupler version - default to 7b
        heatFile = 'cplheatbudget'
        freshWaterFile = 'cplfwbudget'
        cplVersion = 'cpl7b'
        env['ntailht'] = os.environ['ntailht'] = '22'
        env['ntailfw'] = os.environ['ntailfw'] = '16'

        if '7' == env['TS_CPL'] or '6' == env['TS_CPL']:
            cplVersion = 'cpl{0}'.format(env['TS_CPL'])
            env['ntailht'] = os.environ['ntailht'] = '21'
            env['ntailfw'] = os.environ['ntailfw'] = '16'

        # expand the cpl.log* into a list
        cplLogs = list()
        cplLogs = glob.glob('{0}/cpl.log.*'.format(env['WORKDIR']))
        
        cplLogsString = ' '.join(cplLogs)

        # defing the awk command to parse the cpllog file
        heatPath = '{0}/process_{1}_logfiles_heat.awk'.format(env['TOOLPATH'], cplVersion)
        heatPath = os.path.abspath(heatPath)

        fwPath = '{0}/process_{1}_logfiles_fw.awk'.format(env['TOOLPATH'], cplVersion)
        fwPath = os.path.abspath(fwPath)
        
        heatCmd = '{0} y0={1} y1={2} {3}'.format(heatPath, env['YEAR0'], env['YEAR1'], cplLogsString).split(' ')
        freshWaterCmd = '{0} y0={1} y1={2} {3}'.format(fwPath, env['YEAR0'], env['YEAR1'], cplLogsString).split(' ')

        # run the awk scripts to generate the .txt files from the cpllogs
        print('cwd = {0}'.format(os.getcwd()))
        cmdList = [ (heatCmd, heatFile, env['ntailht']), (freshWaterCmd, freshWaterFile, env['ntailfw']) ]
        for cmd in cmdList:
            outFile = '{0}.txt'.format(cmd[1])
            with open (outFile, 'w') as results:
                try:
                    subprocess.check_call(cmd[0], stdout=results, env=env)
                    rc, err_msg = cesmEnvLib.checkFile(outFile, 'read')
                    if rc:
                        # get the tail of the .txt file and redirect to a .asc file for the web
                        ascFile = '{0}.asc'.format(cmd[1])
                        with open (ascFile, 'w') as results:
                            try:
                                #TODO - read the .txt in and write just the lines needed to avoid subprocess call
                                tailCmd = 'tail -{0} {1}.txt'.format(cmd[2], cmd[1]).split(' ')
                                subprocess.check_call(tailCmd, stdout=results, env=env)
                            except subprocess.CalledProcessError as e:
                                print('WARNING: {0} time series error executing command:'.format(self._shortname))
                                print('    {0}'.format(e.cmd))
                                print('    rc = {0}'.format(e.returncode))

                except subprocess.CalledProcessError as e:
                    print('WARNING: {0} time series error executing command:'.format(self._shortname))
                    print('    {0}'.format(e.cmd))
                    print('    rc = {0}'.format(e.returncode))
                    self._awkError = True


    def generate_plots(self, env):
        """Put commands to generate plot here!
        """
        print('  Generating diagnostic plots for : {0}'.format(self.__class__.__name__))

        # chdir into the  working directory
        os.chdir(env['WORKDIR'])

        for ncl in self._ncl:
            # prepend the TS_CPL log value to the ncl plot name
            nclPlotFile = 'cpl{0}_{1}'.format(env['TS_CPL'], ncl)
            
            # copy the NCL command to the workdir
            shutil.copy2('{0}/{1}'.format(env['NCLPATH'],nclPlotFile), '{0}/{1}'.format(env['WORKDIR'], nclPlotFile))

            nclFile = '{0}/{1}'.format(env['WORKDIR'],nclPlotFile)
            rc, err_msg = cesmEnvLib.checkFile(nclFile, 'read')
            if rc:
                try:
                    print('      calling NCL plot routine {0}'.format(nclPlotFile))
                    subprocess.check_call(['ncl', '{0}'.format(nclFile)], env=env)
                except subprocess.CalledProcessError as e:
                    print('WARNING: {0} call to {1} failed with error:'.format(self.name(), nclfile))
                    print('    {0}'.format(e.cmd))
                    print('    rc = {0}'.format(e.returncode))
            else:
                print('{0}... continuing with additional plots.'.format(err_msg))


    def convert_plots(self, workdir, imgFormat):
        """Converts plots for this class
        """
        self._convert_plots(workdir, imgFormat, self._expectedPlots)

    def _create_html(self, workdir, templatePath, imgFormat):
        """Creates and renders html that is returned to the calling wrapper
        """
        plot_table = []
        num_cols = 3

        for i in range(len(self._labels)):
            plot_tuple_list = []
            plot_tuple = (0, 'label','{0}:'.format(self._labels[i]))
            plot_tuple_list.append(plot_tuple)
            plot_list = self._expectedPlots

            for j in range(num_cols - 1):
                if 'timeseries' in self._linkNames[j]:
                    img_file = '{0}.{1}'.format(plot_list[j], imgFormat)
                    rc, err_msg = cesmEnvLib.checkFile( '{0}/{1}'.format(workdir, img_file), 'read' )
                    if not rc:
                        plot_tuple = (j+1, self._linkNames[j],'{0} - Error'.format(img_file))
                    else:
                        plot_tuple = (j+1, self._linkNames[j], img_file)
                    plot_tuple_list.append(plot_tuple)

                elif 'table' in self._linkNames[j]:
                    asc_file = '{0}.{1}'.format(plot_list[j], 'asc')
                    rc, err_msg = cesmEnvLib.checkFile( '{0}/{1}'.format(workdir, asc_file), 'read' )
                    if not rc:
                        plot_tuple = (j+1, self._linkNames[j],'{0} - Error'.format(asc_file))
                    else:
                        plot_tuple = (j+1, self._linkNames[j], asc_file)
                    plot_tuple_list.append(plot_tuple)

            print('DEBUG... plot_tuple_list[{0}] = {1}'.format(i, plot_tuple_list))
            plot_table.append(plot_tuple_list)

        # create a jinja2 template object
        templateLoader = jinja2.FileSystemLoader( searchpath=templatePath )
        templateEnv = jinja2.Environment( loader=templateLoader, keep_trailing_newline=False )

        template = templateEnv.get_template( self._template_file )

        # add the template variables
        templateVars = { 'title' : self._name,
                         'plot_table' : plot_table,
                         'num_rows' : len(self._labels),
                         }

        # render the html template using the plot tables
        self._html = template.render( templateVars )
        
        return self._html

class CplLog_timeseries(CplLog):

    def __init__(self):
        super(CplLog_timeseries, self).__init__()
        self._ncl = ['log_timeseries_heat.ncl', 'log_timeseries_fw.ncl']
