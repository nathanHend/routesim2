from simulator.node import Node
import json
import sys
import copy

INF = sys.maxsize


class Distance_Vector_Node(Node):
    def __init__(self, id):
        super().__init__(id)
        self.str_id = str(id)
        self.seq_num = 0
        # Initialize neighbors and the forwarding table
        self.our_table = {
            self.str_id: {'dst': self.str_id,
            'dist': 0,
            'next_hop': None,
            'path': []}
        }
        self.neighbor_tables = {}
        self.neighbor_seq_nums = {}
        self.outbound_links = {self.str_id: 0}
        # self.print_dv_table(self.str_id)

    # Return a string
    def __str__(self):
        return "Rewrite this function to define your node dump printout"

    # Fill in this function
    def link_has_been_updated(self, neighbor, latency):
        neighbor = str(neighbor)
        # Check if the link was deleted (AKA latency == -1)
        if latency == -1:
            if neighbor not in self.outbound_links.keys():
                return
            del self.outbound_links[neighbor]
            del self.neighbor_tables[neighbor]
        # We are changing the link dist!
        elif latency != self.outbound_links.get(neighbor, -1):
            self.outbound_links[neighbor] = latency
        else:
            return
        # Update the dv
        self._update_dv()

    # Fill in this function
    def process_incoming_routing_message(self, m):
        neighbor, seq_num, neighbor_table = json.loads(m)
        # Check if the sequence number is invalid
        if seq_num > self.neighbor_seq_nums.get(neighbor, -1):
            if neighbor not in self.outbound_links.keys():
                print(f"We ({self.str_id}) could not find this neighbor", neighbor)
                return
            # Set sequence number
            self.neighbor_seq_nums[neighbor] = seq_num
            self.neighbor_tables[neighbor] = neighbor_table
            self._update_dv()

    # Return a neighbor, -1 if no path to destination
    def get_next_hop(self, destination):
        destination = str(destination)
        if destination in self.our_table.keys() and destination != str(self.id):
            return int(self.our_table[destination]['next_hop'])
        return -1

    # Print our/neighbor DV table
    def print_dv_table(self, dv_id):
        print(f"DV Table for {dv_id}")
        table = self.our_table if dv_id == self.str_id else self.neighbor_tables[dv_id]
        for entry in table.values():
            print(f"<{entry['dst']}, {entry['dist']}, {entry['next_hop']}, {entry['path']}>")

    def diff_dvs(self, dv1: dict, dv2: dict) -> bool:
        # Check easy case
        if len(dv1) != len(dv2):
            return True
        return dv1 != dv2

    def _update_dv(self):
        # New DV to compute
        new_dv = {}
        # Add local connections
        for dst, lat in self.outbound_links.items():
            new_dv[dst] = {
                'dst': dst,
                'dist': lat,
                'next_hop': dst if lat > 0 else None,
                'path': [dst] if lat > 0 else []
            }

        # Compute a new DV and check if there is a change
        for n_id, table in self.neighbor_tables.items():
            # Loop through each entry
            for dst, entry in table.items():
                new_dist = entry['dist'] + self.outbound_links[n_id]
                # Check if path contains loop
                if self.str_id in entry['path']:
                    continue
                # Check if the path is better
                if dst not in new_dv.keys() or new_dist < new_dv[dst]['dist']:
                    # Add the new dest
                    new_dv[dst] = {
                        'dst': dst,
                        'dist': new_dist,
                        'next_hop': n_id,
                        'path': [n_id] + entry['path']
                    }
        # Check if there has been a change
        if self.diff_dvs(self.our_table, new_dv):
            # Change our dv
            self.our_table = new_dv
            # Print dv
            # self.print_dv_table(self.str_id)
            self.send_to_neighbors(json.dumps([self.str_id, self.seq_num, new_dv]))
            self.seq_num += 1
