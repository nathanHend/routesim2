from simulator.node import Node
import json
import sys

INF = sys.maxsize


class Distance_Vector_Node(Node):
    def __init__(self, id):
        super().__init__(id)
        self.str_id = str(id)
        self.seq_num = 0
        # Initialize neighbors and the forwarding table
        self.our_table = {
            self.str_id: {
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
        lat_diff = None
        # Check if the link was deleted (AKA latency == -1)
        if latency == -1:
            if neighbor not in self.outbound_links.keys():
                return
            del self.outbound_links[neighbor]
            del self.neighbor_tables[neighbor]
        # We are changing the link dist!
        elif latency != self.outbound_links.get(neighbor, -1):
            lat_diff = latency - self.outbound_links.get(neighbor, 0)
            self.outbound_links[neighbor] = latency
        else:
            return
        # Update the dv
        self._update_fast_link(neighbor, lat_diff)

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
            # Copy neighbor table
            self.neighbor_tables[neighbor] = neighbor_table
            self._update_fast_dv(neighbor)

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
        for dst, entry in table.items():
            print(f"<{dst}, {entry['dist']}, {entry['next_hop']}, {entry['path']}>")

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

    def _update_fast_dv(self, neighbor):
        # Theoretically, we only need to modify anyone whose next step is the changed neighbor
        # Or whose is better
        # Loop through every entry in our DV,
        # Always check if the updated neighbor's path is better
        # Else, check if the next step is equal to our neighbor and the distance is longer
        # Check the paths for all the other neighbors to see if something is better
        # If none exist, delete path
        delete_keys = []
        updated = False
        # Loop through our entries
        for key, entry in self.our_table.items():
            # Get the corresponding path
            neighbor_entry = self.neighbor_tables[neighbor].get(key, None)
            # Check if the next step is our neighbor
            if entry['next_hop'] == neighbor:
                # Check if the path exists or path is worse
                if neighbor_entry is None or neighbor_entry['dist'] + self.outbound_links[neighbor] > entry['dist']:
                    # We need to update our table
                    updated = True
                    delete = neighbor is None

                    # Check if we did not delete that entry
                    if neighbor_entry is not None:
                        # Change the path
                        entry['dist'] = neighbor_entry['dist'] + self.outbound_links[neighbor]
                        entry['next_hop'] = neighbor
                        entry['path'] = [neighbor] + neighbor_entry['path']

                    # Check direct connection
                    if key in self.outbound_links:
                        if delete or self.outbound_links[key] < entry['dist']:
                            # Change the path
                            entry['dist'] = self.outbound_links[key]
                            entry['next_hop'] = key
                            entry['path'] = [key]

                    # Loop through neighbors and try to find the best path for that key
                    for n, table in self.neighbor_tables.items():
                        if key in table.keys():
                            if delete or table[key]['dist'] + self.outbound_links[n] < entry['dist']:
                                # We no longer delete is
                                delete = False
                                # Change the path
                                entry['dist'] = table[key]['dist'] + self.outbound_links[n]
                                entry['next_hop'] = n
                                entry['path'] = [n] + table[key]['path']
                    if delete:
                        delete_keys.append(key)
                    continue

            # Check if path exists
            if neighbor_entry is None:
                continue
            # Check if neighbor path contains a loop
            if self.str_id in neighbor_entry['path']:
                continue
            # Check if neighbor path is better
            if neighbor_entry['dist'] + self.outbound_links[neighbor] < entry['dist']:
                # Change the path
                entry['dist'] = neighbor_entry['dist'] + self.outbound_links[neighbor]
                entry['next_hop'] = neighbor
                entry['path'] = [neighbor] + neighbor_entry['path']
                # We changed something!
                updated = True

        # Delete pair that no longer exist
        for key in delete_keys:
            del self.our_table[key]

        # Add pairs that don't exist in our table
        for key, entry in self.neighbor_tables[neighbor].items():
            if key not in self.our_table.keys():
                self.our_table[key] = {
                    'dist': entry['dist'] + self.outbound_links[neighbor],
                    'next_hop': neighbor,
                    'path': [neighbor] + entry['path']
                }
                updated = True

        if updated:
            self.send_to_neighbors(json.dumps([self.str_id, self.seq_num, self.our_table]))
            self.seq_num += 1

    def _update_fast_link(self, neighbor, lat_diff):
        # We should be able to loop through each entry in our table
        # If the link has decreased:
        #   We update every path that uses the link
        #   We check if a path using the link is better
        # If the link has increased or deleted:
        #   We update every path that uses the link
        #   Then we check if there is a better path not using the link

        delete_keys = []
        updated = False
        # Loop through our table
        for key, entry in self.our_table.items():
            # Update the link
            if entry['next_hop'] == neighbor:
                updated = True
                # If the link was not deleted, change the lat
                if lat_diff is not None:
                    entry['dist'] += lat_diff

                # Check if link was deleted or increased
                if lat_diff is None or lat_diff > 0:
                    # We need to update our table
                    delete = lat_diff is None

                    # Loop through neighbors and try to find the best path for that key
                    for n, table in self.neighbor_tables.items():
                        if key in table.keys():
                            if delete or table[key]['dist'] + self.outbound_links[n] < entry['dist']:
                                # We no longer delete is
                                delete = False
                                # Change the path
                                entry['dist'] = table[key]['dist'] + self.outbound_links[n]
                                entry['next_hop'] = n
                                entry['path'] = [n] + table[key]['path']
                    if delete:
                        delete_keys.append(key)
                    continue
            # Check for better links if we decreased lat
            elif lat_diff is not None and lat_diff < 0:
                # Check that the neighbor exists
                if neighbor in self.neighbor_tables.keys():
                    # Check if we have a better path
                    if key in self.neighbor_tables[neighbor].keys():
                        # Check if the path is better
                        if self.outbound_links[neighbor] + self.neighbor_tables[neighbor][key]['dist'] < entry['dist']:
                            # We updated our DV
                            updated = True
                            entry['dist'] = self.outbound_links[neighbor] + self.neighbor_tables[neighbor][key]['dist']
                            entry['next_hop'] = neighbor
                            entry['path'] = [neighbor] + self.neighbor_tables[neighbor][key]['path']

        for key in delete_keys:
            del self.our_table[key]

        # Check if neighbor exists and we are adding a link
        if neighbor not in self.our_table.keys() and lat_diff is not None:
            updated = True
            self.our_table[neighbor] = {
                'dist': lat_diff,
                'next_hop': neighbor,
                'path': [neighbor]
            }

        if updated:
            self.send_to_neighbors(json.dumps([self.str_id, self.seq_num, self.our_table]))
            self.seq_num += 1
