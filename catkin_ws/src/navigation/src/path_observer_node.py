
import sys 
import os
import rospy
scriptLoc = os.path.dirname(__file__)
addloc = scriptLoc[0:len(scriptLoc)-18] + "src\\navigation\include\\navigation"

sys.path.append(addloc)

#import generate_duckietown_map as gdm
from graph import Graph

test = 0 # set to 1 for testing map changing code, set to 0 for normal run

class PathObserverNode():
    def __init__(self):
        self.node_name = rospy.get_name()

        # Parameters: - copied from ActionsDispatcherNode, unsure what this should be
        """
        self.fsm_mode = self.setupParameter("~initial_mode","JOYSTICK_CONTROL")
        self.localization_mode = self.setupParameter("~localization_mode","LOCALIZATION")
        self.trigger_mode = self.setupParameter("~trigger_mode","INTERSECTION_CONTROL")
        self.reset_mode = self.setupParameter("~reset_mode","JOYSTICK_CONTROL")
        """
        # graph_search_server_node must initialize BEFORE this code runs!
        self.wgraph = rparam2graph()
        
        self.current_node = rospy.get_param('current_node')
        #if current node isn't at an intersection, have to do some propagation
        if self.current_node[0:3] == 'turn': #ensure that last_int_node is actually at an intersection
            current_edge_set = w_graph._edges[last_node]
            for i in [1, 2]:
                #traversing forward to next intersection
                while len(current_edge_set) == 1: #haven't reached an intersection yet
                    # find edge(s) after the one we're on
                    current_edge_set = w_graph._edges[next(iter(current_edge_set)).target]
                    last_node = next(iter(current_edge_set)).source

                #reached the next intersection
                u_turn_lut = get_flip_lut()
                last_node = u_turn_lut[next(iter(current_edge_set)).source]
                
                #repeat the process going in the anti-parallel lane
                current_edge_set = w_graph._edges[last_node]
                
            self.current_node = last_node            
                
        
        # Subscribers:
        #road block detected
        self.sub_rb = rospy.Subscriber('~road_blocked', BoolStamped, self.handle_road_blocked)
        #turning
        self.sub_turn = rospy.Subscriber("~turn_type", Int16, self.propagate_location)
                

        # Publishers:      
        #indicate that we're ready to traverse a path(?)
        self.pub_ready = rospy.Publisher("~plan_generated", BoolStamped, queue_size=1, latch=True)
        #publish to here to request an a* search from ActionsDispatcherNode
        self.pub_plan_request = rospy.Publisher("~plan_request", SourceTargetNodes)
  
    def onShutdown():
        rospy.loginfo("[PathObserverNode] Shutdown.")

    def handle_road_blocked(data):
        # runs when a complete roadblock is seen
        # has to update the graph that the path planning server is using
        
        # modify working graph
        self.wgraph = self.destroy_edges(current_node, self.wgraph)     
        
        # write working graph to ros parameters
        graph2rparam(self.wgraph)
        
    def propagate_location(data):
        # run each time a turn command is issued; follow along in the graph
        # needs access to the most up to date graph and turn info
        possible_edges = self.wgraph._edges[self.current_node]
            
        actionLUT = {1:'s', 2:'r', 0:'l'}
        
        for edge in possible_edges:
            if edge.action == actionLUT[data]:            
                self.current_node = edge.target
                break
    
    def rparam2graph():
        return Graph(None, rospy.get_param("duckie_graph_nodes"), rospy.get_param("duckie_graph_edges"), set(rospy.get_param("duckie_graph_pos")))
        
    def graph2rparam(gr):
        rospy.set_param("duckie_graph_edges",gr._edges)
        rospy.set_param("duckie_graph_pos",gr.node_positions)
        rospy.set_param("duckie_graph_nodes",list(gr._nodes))        
        

    def destroy_edges(last_node, orig_graph):
        # this is to be called when the current edge is a completely blocked road
        # traverse edges forward until the next numbered node while deleting
        # use flip LUT to delete the lane anti-parallel to the path just travelled
        
        # Doesn't work for blockages in intersections (yet...)
        
            
        # make a working copy of the graph        
        #w_graph = Graph(orig_graph.node_label_fn,orig_graph._nodes,orig_graph._edges,orig_graph.node_positions)
        w_graph = orig_graph.copy()
        
        
        current_edge_set = w_graph._edges[last_node]
        for i in [1, 2]:
            #traversing forward to next intersection
            while len(current_edge_set) == 1: #haven't reached an intersection yet
                # delete the current edge
                w_graph._edges[last_node] = w_graph._edges[last_node] - current_edge_set
                # find edge(s) after the one we're on
                current_edge_set = w_graph._edges[next(iter(current_edge_set)).target]
                last_node = next(iter(current_edge_set)).source
                    
            if i == 2: break
            #reached the next intersection
            u_turn_lut = get_flip_lut()
            last_node = u_turn_lut[next(iter(current_edge_set)).source]
            
            #repeat the process going in the anti-parallel lane
            current_edge_set = w_graph._edges[last_node]
        
        return w_graph

    def get_flip_lut():
        # look up table for u-turn node results. For every node at an intersection, this contains the node in the opposite lane closest to the current node
        # In the future, this LUT could be autogenerated from the data in the map csv. Once that data is used to generate a graph, it's harder to use that data to generate the lut
        
        # keys: current node
        # entries: node in other direction
        # no particular order to these
        u_turn_lut = {'1':'6',
                      '2':'3',
                      '4':'5',
                      '7':'12',
                      '8':'9',
                      '10':'11',
                      '13':'20',
                      '14':'15',
                      '16':'17',
                      '18':'19',
                      '21':'26',
                      '22':'23',
                      '24':'25',
                      '32':'27',
                      '28':'29',
                      '30':'31',
                      }
    
        # autogenerate the LUT that reverses all these key, entry pairs
        second_half_u_turn_lut = {}
        for key in u_turn_lut.keys():
            second_half_u_turn_lut[u_turn_lut[key]] = key
            
        #print len(u_turn_lut.keys())
        
        # add the autogenerated content to the original
        u_turn_lut.update(second_half_u_turn_lut)
        #print len(u_turn_lut.keys())
        return u_turn_lut           
        
        
if __name__ == "__main__":
    
    if test:
        gc = gdm.graph_creator()
        #duckietown_graph = gc.build_graph_from_csv(csv_filename='tiles_226')
        duckietown_graph = gc.build_graph_from_csv(csv_filename='tiles_jec5312')
        
        # Node locations (for visual representation) and heuristics calculation
        #node_locations, edges = gc.get_map_226()
        #gc.add_node_locations(node_locations)
        #gc.add_edges(edges)
        #gc.pickle_save()
        scriptLoc = os.path.dirname(__file__)
        mapLoc = scriptLoc
        duckietown_graph.draw(mapLoc,map_name='duckietown_jec5312')
        
        myPON = PathObserverNode()
        duckietown_graph_modified = myPON.destroy_edges('7',duckietown_graph);
        duckietown_graph_modified.draw(mapLoc,map_name='duckietown_jec5312_mod')
    else:
        #normal runtime code    
        rospy.init_node('path_observer_node')
        path_observer_node = PathObserverNode()
        rospy.on_shutdown(path_observer_node.onShutdown)
        rospy.spin()    
