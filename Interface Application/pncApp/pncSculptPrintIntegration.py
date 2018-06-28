import pncLibrary
import multiprocessing, os, sys, time, logging, numpy as np
#from pncCamUserInterface import CAM_MVC

#print('Current PYTHONPATH is ' + str(sys.path))
#pncApp_project_path = 'C:\\Users\\robyl_000\\Documents\\Projects\\PocketNC\\MachineKitOpenCNC\\Interface Application\\pncApp\\'


#Globals
#sculptprint_MVC = None

#There are two set of axis sensors: stepgens (0) and encoders (1)
axis_sensor_id = [0, 1]
SP_data_formats = [['T','X','Z','S','Y','A','B','V','W','BL'], ['T','X','Z','S','Y','A','B','V','W']]

############################# Setup Functions #############################

def monitoredMachineCount():
    return 2

def setupMachineAuxilary():
    return setupAuxiliary()

def setupAuxiliary():
    #stringArray = [r'C', r'sinx', r'fx', r'gx', r'fx+gx', r'cos+cos', r'cos*sin', r'stepf']
    stringArray = [r'Buffer Level']
    return stringArray

def setupMachineAuxilary(nMachine):
    return setupMachineAuxiliary(nMachine)

def setupMachineAuxiliary(nMachine):
    if nMachine == 0:
        stringArray = [r'Buffer Level']
    else:
        stringArray = ['']
    return stringArray

def setupMachineDescriptors(nMachine):
    #columnTypeArray = []
    if nMachine == 0:
        #Monitoring from BBB gives stepgen position and buffer level
        columnTypeArray = [0, 1, 1, 1, 1, 1, 1, 1, 1, 2]
    else:
        #Encoder positions are only time and axis position
        columnTypeArray = [0, 1, 1, 1, 1, 1, 1, 1, 1]
    return columnTypeArray

def setupUserDataNames():
    stringArray = [r'Start File', r'End File', r'my data 3', r'my data 4', r'my data 5']
    return stringArray

# Returns an array of user defined function names that are displayed on the function buttons in the feature UI. The array affects
# feature UI functionality only.  The array must be sized on the interval [1,3]. Defining this method is optional.
def setupUserFunctionNames():
    stringArray = [r'Initialize Control',r'Enqueue Movements',r'Execute Motion']
    return stringArray

############################# Data Handling #############################

def findNextClosestTimeIndex(sample_time,data_time_array):
    if len(data_time_array) == 0:
        return -1

    delta_T = data_time_array - sample_time
    future_delta_T = delta_T[np.where(delta_T >= 0)]
    if len(future_delta_T) == 0:
        #Requested time is out of bounds for given time vector
        return -2

    time_index = future_delta_T.argmin() + len(delta_T[delta_T < 0])
    return time_index


def formatFeedbackDataForSP(machine, sensor_type, times, positions, auxes=[]):
    #SP_formatted_data = len(times) * [[0] * len(SP_data_format)]
    SP_formatted_data = []
    for data_point_index in range(0,len(times)):
        if len(auxes):
            time, position, aux = (times[data_point_index], positions[data_point_index], auxes[data_point_index])
        else:
            time, position = (times[data_point_index], positions[data_point_index])
        data_point = [0] * len(SP_data_formats[sensor_type])
        for label in range(0,len(SP_data_formats[sensor_type])):
            label_text = SP_data_formats[sensor_type][label]
            if label_text == 'X':
                data_point[label] = float(position[0])
            elif label_text == 'Y':
                data_point[label] = float(position[1])
            elif label_text == 'Z':
                data_point[label] = float(position[2])
            elif label_text == 'A':
                data_point[label] = float(position[3])
            elif label_text == 'B':
                data_point[label] = float(position[4])
            elif label_text == 'T':
                data_point[label] = float(time)
            elif label_text == 'BL':
                data_point[label] = float(aux)
            elif label_text == 'S':
                data_point[label] = -90.0
            else:
                data_point[label] = 0.0
        SP_formatted_data.append(data_point)
    return SP_formatted_data

def mergeSortByIndex(machine, feedback_state, times_LF, times_HF, data_LF, data_HF):
    LF_index, HF_index = (0, 0)
    #output_data = []
    output_times, output_positions, output_auxes = [], [], []
    while LF_index != times_LF.size and HF_index != times_HF.size:
        if times_LF[LF_index] < times_HF[HF_index]:
            data_time = times_LF[LF_index]
            data_position = data_LF[LF_index]
            if HF_index-1 < 0:
                #data_aux = 0
                #data_aux = machine.rsh_buffer_level
                data_aux = feedback_state.last_buffer_level_reading
            else:
                data_aux = data_HF[HF_index-1]
            LF_index += 1
        elif times_LF[LF_index] == times_HF[HF_index]:
            data_time = times_LF[LF_index]
            data_position = data_LF[LF_index]
            data_aux = data_HF[HF_index]
            LF_index += 1
            HF_index += 1
        else:
            #output_index_list.append((0, index2))
            data_time = times_HF[HF_index]
            if LF_index - 1 < 0:
                #data_position = machine.current_position
                data_position = feedback_state.last_position_reading
            else:
                data_position = data_LF[LF_index-1]
            data_aux = data_HF[HF_index]
            HF_index += 1
        #data_point = formatFeedbackDataForSP(data_time, data_positions, data_aux)
        output_times.append(data_time)
        output_positions.append(data_position)
        output_auxes.append(data_aux)
        #output_data.append(data_point)

    while LF_index != times_LF.size:
        #output_index_list.append((0,index1))
        data_time = times_LF[LF_index]
        data_position = data_LF[LF_index]
        if HF_index - 1 < 0:
            #data_aux = machine.rsh_buffer_level
            data_aux = feedback_state.last_buffer_level_reading
        else:
            data_aux = data_HF[HF_index - 1]
        LF_index += 1
        #data_point = formatFeedbackDataForSP(data_time, data_positions, data_aux)
        output_times.append(data_time)
        output_positions.append(data_position)
        output_auxes.append(data_aux)
        #output_data.append(data_point)

    while HF_index != times_HF.size:
        #output_index_list.append((1,index2))
        data_time = times_HF[HF_index]
        if LF_index - 1 < 0:
            #data_position = machine.current_position
            #data_position = machine.sculptprint_interface.last_position_reading
            data_position = feedback_state.last_position_reading
        else:
            data_position = data_LF[LF_index - 1]
        data_aux = data_HF[HF_index]
        HF_index += 1
        #FIXME do this in readMachine instead
        #data_point = formatFeedbackDataForSP(data_time, data_positions, data_aux)
        output_times.append(data_time)
        output_positions.append(data_position)
        output_auxes.append(data_aux)
        #output_data.append(data_point)

    return output_times, output_positions, output_auxes, LF_index, HF_index

    # if len(output_times) > 0:
    #     #return output_data, LF_index, HF_index
    #     return output_times, output_positions, output_auxes, LF_index, HF_index
    # return None, None, None, 0, 0

def readMachine(machine, synchronizer, feedback_state, axis_sensor_id):
    #global machine
    #global feedback_listener, machine_controller, encoder_interface, data_store
    #global LF_start_time_index, HF_start_time_index#, highfreq_rx_time, lowfreq_rx_time
    if synchronizer.mvc_run_feedback_event.is_set():
        if axis_sensor_id == 0:
            ## FIXME check that logging is enabled and that threads are set up right
            #Snapshot data store

            DB_query_data = pncLibrary.lockedPull(synchronizer, ['RSH_CLOCK_TIMES','HIGHRES_TC_QUEUE_LENGTH','RTAPI_CLOCK_TIMES','STEPGEN_FEEDBACK_POSITIONS'],
                                                  [feedback_state.HF_start_time_index,feedback_state.HF_start_time_index,feedback_state.LF_start_time_index,feedback_state.LF_start_time_index],
                                                  4*[None])

            #Data were gotten from DB
            HF_ethernet_time_slice, HF_ethernet_data_slice, LF_ethernet_time_slice, LF_ethernet_data_slice = DB_query_data[1]

            # if len(HF_ethernet_data_slice) == 0 and len(LF_ethernet_data_slice) == 0:
            #     return []

            #BBB_feedback, LF_start_time_index_increment, HF_start_time_index_increment = mergeSortByIndex(LF_ethernet_time_slice,HF_ethernet_time_slice,LF_ethernet_data_slice,HF_ethernet_data_slice)
            times, positions, auxes, LF_start_time_index_increment, HF_start_time_index_increment = mergeSortByIndex(
                machine, feedback_state, LF_ethernet_time_slice, HF_ethernet_time_slice, LF_ethernet_data_slice, HF_ethernet_data_slice)

            feedback_state.LF_start_time_index += LF_start_time_index_increment
            feedback_state.HF_start_time_index += HF_start_time_index_increment
            #print(LF_start_time_index)
            # if any([d is None for d in [times, positions, auxes]]):
            #     return []
            # else:
            feedback_state.last_time_reading = times[-1] if len(times) > 0 else 0
            feedback_state.last_position_reading = positions[-1] if len(positions) > 0 else machine.number_of_joints*[0]
            feedback_state.last_buffer_level_reading = auxes[-1] if len(auxes) > 0 else 0
            #BBB_feedback = formatFeedbackDataForSP(axis_sensor_id, times, positions, auxes)
            #print('HF ethernet data slice is ' + str(HF_ethernet_data_slice))

            return formatFeedbackDataForSP(machine, axis_sensor_id, times, positions, auxes)

        elif axis_sensor_id == 1:
            DB_query_data = pncLibrary.lockedPull(synchronizer, ['SERIAL_RECEIVED_TIMES', 'ENCODER_FEEDBACK_POSITIONS'],
                                                  2*[feedback_state.serial_start_time_index],
                                                  2*[None])

            serial_time_slice, serial_data_slice = DB_query_data[1]
            feedback_state.serial_start_time_index += len(serial_data_slice)

            return formatFeedbackDataForSP(machine, axis_sensor_id, serial_time_slice, serial_data_slice)
    return []

    # else:
    #     return np.asarray([[0, 1, 1, 1, 1, 1, 1, 1, 1]], dtype=float).tolist()

# Returns true if monitoring is currently happening.
def isMonitoring(synchronizer):
    try:
        monitoring_flag = synchronizer.process_start_signal.is_set() and synchronizer.mvc_run_feedback_event.is_set()
    except NameError:
        print('Synchronizer not set up yet')
        monitoring_flag = False
    return monitoring_flag
    #return synchronizer.process_start_signal.is_set()
    #return bool(machine.machine_controller_thread_handle.is_alive() & machine.servo_feedback_mode)

############################# User Functions #############################
def userPythonFunction1(arg0, arg1, arg2, arg3, arg4):
    sculptprint_MVC.command_queue.put('CONNECT')


# def userPythonFunction1(arg0, arg1, arg2, arg3, arg4):
#     #global machine
#     print('execute enqueueMoves from ' + str(arg0) +' to ' + str(arg1))#(' + str(arg0) + ',' + str(arg1) + ',' + str(arg2) + ',' + str(arg3) + ',' + str(arg4) + ')\n')
#     #machine_controller.testMachine(1,1,1,1,1)
#     #machine_controller.motion_controller._running_motion = True
#     machine.sculptprint_interface.start_file = arg0
#     machine.sculptprint_interface.end_file = arg1
#     machine.sculptprint_interface.enqueue_moves_event.set()
#     return True;

def userPythonFunction2(arg0, arg1, arg2, arg3, arg4):
    print('execute userPythonFunction2(' + str(arg0) + ',' + str(arg1) + ',' + str(arg2) + ',' + str(arg3) + ',' + str(arg4) + ')\n')
    sculptprint_MVC.command_queue.put('ENQUEUE ' + str(arg0) + ' ' + str(arg1))
    return True;

def userPythonFunction3(arg0, arg1, arg2, arg3, arg4):
    print('execute userPythonFunction3(' + str(arg0) + ',' + str(arg1) + ',' + str(arg2) + ',' + str(arg3) + ',' + str(arg4) + ')\n')
    sculptprint_MVC.command_queue.put('EXECUTE')
    return True;

# def connectToMachine():
#     sculptprint_MVC.command_queue.put('CONNECT')

# Called to stop monitoring the machine.
# Will execute when the stop button is pressed in the Monitor Machine feature.
def stop(synchronizer):
    #print('closing')
    #appClose()
    sculptprint_MVC.command_queue.put('CLOSE')
    synchronizer.mvc_app_shutdown_event.wait()
    return True

def testMonitoring():
    while True:
        z = readMachine(0)
        if z == []:
            print('returning nothing')
        else:
            print('returning good data')
        print('read machine')

# if False:
#     read_data0 = []
#     time_to_read0 = []
#     read_data1 = []
#     start()
#     machine.sculptprint_interface.enqueue_moves_event.set()
#     machine.sculptprint_interface.run_motion_event.set()
#     while True:
#         start = time.clock()
#         data0 = readMachine(0)
#         time_to_read0.append(time.clock()-start)
#         data1 = readMachine(1)
#         #print(data)
#         if data0 != []:
#             print('appending data0')
#             read_data0.append(data0)
#         if data1 != []:
#             print('appending data1')
#             read_data1.append(data1)
    #else:
        #print('not appending data')

#time.sleep(1)
#readMachine(0)
#
# while True:
#     readMachine(0)
# print('here')
# if __name__ == '__main__':
#     start()

#multiprocessing.set_executable(os.path.join(sys.exec_prefix, 'pythonw.exe'))
#multiprocessing.set_start_method('spawn')
#print('main name is ' + str(__name__))
