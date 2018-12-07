#!/usr/bin/env python

import sys
import rospy
from navigation.srv import *
from duckietown_msgs.msg import FSMState, SourceTargetNodes, BoolStamped, Twist2DStamped
from std_msgs.msg import Int16, String

class ActionsDispatcherNode():
    def __init__(self):
        self.node_name = rospy.get_name()

        #adding logic because FSM publishes our state at a high rate
        #not just everytime the mode changes but multiple times in each mode
        self.first_update = True

        self.actions = []
	# I think all of these are set in the .yaml file... try commenting them out
        # Parameters:
        self.fsm_mode = self.setupParameter("~initial_mode","LANE_FOLLOWING")
        self.localization_mode = self.setupParameter("~localization_mode","LOCALIZATION")
        self.trigger_mode = self.setupParameter("~trigger_mode","INTERSECTION_CONTROL")
	# Performs a reset so don't set to lane following
        self.reset_mode = self.setupParameter("~reset_mode","JOYSTICK_CONTROL")
        self.stop_line_wait_time = self.setupParameter("~stop_line_wait_time",2.0)
	# Putting this in bc rqt isnt' working? need to figure out what was publishing this before
	#self.veh = self.setupParameter("/veh", "howard17")
        # Subscribers:
        self.sub_mode = rospy.Subscriber("~fsm_mode", FSMState, self.updateMode, queue_size = 1)
        self.sub_plan_request = rospy.Subscriber("~plan_request", SourceTargetNodes, self.graph_search)

        # Publishers:
        self.pub = rospy.Publisher("~turn_type", Int16, queue_size=1, latch=True)
        self.pubList = rospy.Publisher("~turn_plan", String, queue_size=1, latch=True)
        self.pub_localized = rospy.Publisher("~localized", BoolStamped, queue_size=1, latch=True)

    def setupParameter(self,param_name,default_value):
        value = rospy.get_param(param_name,default_value)
        rospy.set_param(param_name,value) #Write to parameter server for transparancy
        rospy.loginfo("[%s] %s = %s " %(self.node_name,param_name,value))
        return value

    def updateMode(self, data):
        self.fsm_mode = data.state
        if self.fsm_mode == self.reset_mode:
            self.actions = []
            rospy.wait_for_service('graph_search')
            graph_search = rospy.ServiceProxy('graph_search', GraphSearch)
            graph_search('0', '0')
        elif self.localization_mode != "none" and self.fsm_mode == self.localization_mode:
            self.pubLocalized()
        self.dispatcher()

    def dispatcher(self):
        if self.first_update == False and self.fsm_mode != self.trigger_mode:
            self.first_update = True

	# If its the first update, and we're in intersection control, and ?? (actions ins't empty?)
        if self.first_update == True and self.fsm_mode == self.trigger_mode and self.actions:
            # Allow time for open loop controller to update state and allow duckiebot to stop at redline:
            rospy.sleep(self.stop_line_wait_time)
        
            # Proceed with action dispatching:
            action = self.actions.pop(0)
            print 'Dispatched:', action
            if action == 's':
                self.pub.publish(Int16(1))
            elif action == 'r':
                self.pub.publish(Int16(2))
            elif action == 'l':
                self.pub.publish(Int16(0))
            elif action == 'w':
                self.pub.publish(Int16(-1))    
    
            action_str = ''
            for letter in self.actions:
                action_str += letter

            self.pubList.publish(action_str)
            self.firstUpdate = False

    def graph_search(self, data):
        print('Requesting map for src: ', data.source_node, ' and target: ', data.target_node)
        rospy.wait_for_service('graph_search')
        try:
            graph_search = rospy.ServiceProxy('graph_search', GraphSearch)
            resp = graph_search(data.source_node, data.target_node)
            self.actions = resp.actions
            if self.actions:
                # remove 'f' (follow line) from actions and add wait action in the end of queue
                self.actions = [x for x in self.actions if x != 'f']
                self.actions.append('w')
                print 'Actions to be executed:', self.actions
                action_str = ''
                for letter in self.actions:
                    action_str += letter
                self.pubList.publish(action_str)
                self.dispatcher()
            else:
                print 'Actions to be executed:', self.actions

        except rospy.ServiceException, e:
            print "Service call failed: %s"%e

    def pubLocalized(self):
        msg = BoolStamped()
        msg.data = True
        self.pub_localized.publish(msg)

    def onShutdown(self):
        rospy.loginfo("[ActionsDispatcherNode] Shutdown.")

if __name__ == "__main__":
    rospy.init_node('actions_dispatcher_node')
    actions_dispatcher_node = ActionsDispatcherNode()
    rospy.on_shutdown(actions_dispatcher_node.onShutdown)
    rospy.spin()
