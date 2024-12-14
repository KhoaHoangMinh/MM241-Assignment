from policy import Policy


class Policy2210xxx(Policy):
    def __init__(self, policy_id=1):
        assert policy_id in [1, 2], "Policy ID must be 1 or 2"
        self.policy_id = policy_id  # Store the policy ID
        # Student code here
        if policy_id == 1:
            self.current_placements = []
            self.free_rectangles = {}  # Dict[stock_idx, List[tuple]] storing (x, y, w, h)
            self.initial_stocks = []  # Store initial stocks for reset
            
        elif policy_id == 2:
            self.current_placements = []
            self.free_rectangles = {}  # Dict[stock_idx, List[tuple]] storing (x, y, w, h)
            self.initial_stocks = []  # Store initial stocks for reset
            pass

    def get_action(self, observation, info):
        # Student code here
        # Check if filled_ratio is 0.00 to determine if a reset is needed
        if info.get("filled_ratio", 1.00) == 0.00:
            self.reset()

        # Store initial stocks on the first call
        if not self.initial_stocks:
            self.initial_stocks = observation["stocks"]

        if not self.current_placements:
            # Get products and sort by area
            products = [prod for prod in observation["products"] if prod["quantity"] > 0]
            products.sort(key=lambda x: x["size"][0] * x["size"][1], reverse=True)

            # Use appropriate placement strategy based on policy_id
            if self.policy_id == 1:
                self.current_placements = self._place_guillotine(products, observation)
            else:  # policy_id == 2
                self.current_placements = self._place_best_fit(products, observation)  # New heuristic placement strategy

            if not self.current_placements:
                # Return a default action if no placements are available
                return {"stock_idx": 0, "size": [0, 0], "position": (0, 0)}

        # Return the next placement
        return self.current_placements.pop(0)


    # Student code here
    # You can add more functions if needed
    def _split_rectangle(self, rect, prod_size):
        """
        Guillotine split scheme to subdivide rectangle into F' and F''
        rect: tuple (x, y, width, height)
        prod_size: tuple (width, height)
        Returns: List of new rectangles after split
        """
        x, y, w, h = rect
        prod_w, prod_h = prod_size
        new_rects = []

        # Split horizontally (F')
        if h > prod_h:
            new_rects.append((x, y + prod_h, w, h - prod_h))

        # Split vertically (F'')
        if w > prod_w:
            new_rects.append((x + prod_w, y, w - prod_w, prod_h))

        return new_rects

    def _merge_rectangles(self, stock_idx):
        """
        Merge adjacent rectangles in the stock if possible
        """
        if stock_idx not in self.free_rectangles:
            return

        free_rects = self.free_rectangles[stock_idx]
        merged = True

        while merged:
            merged = False
            i = 0
            while i < len(free_rects):
                j = i + 1
                while j < len(free_rects):
                    r1 = free_rects[i]
                    r2 = free_rects[j]
                    x1, y1, w1, h1 = r1
                    x2, y2, w2, h2 = r2

                    # Try horizontal merge (same height and y-position)
                    if h1 == h2 and y1 == y2 and x1 + w1 == x2:
                        # Merge r1 and r2 horizontally
                        free_rects[i] = (x1, y1, w1 + w2, h1)
                        free_rects.pop(j)
                        merged = True
                        break

                    # Try vertical merge (same width and x-position)
                    if w1 == w2 and x1 == x2 and y1 + h1 == y2:
                        # Merge r1 and r2 vertically
                        free_rects[i] = (x1, y1, w1, h1 + h2)
                        free_rects.pop(j)
                        merged = True
                        break

                    j += 1

                if merged:
                    break
                i += 1

    def _find_best_area_fit(self, prod_size, stock_idx, stock):
        """
        Find the rectangle with the smallest area difference compared to the product
        Returns: rect or None if no fit found
        """
        prod_w, prod_h = prod_size
        prod_area = prod_w * prod_h
        best_rect = None
        min_area_diff = float('inf')

        for rect in self.free_rectangles[stock_idx]:
            x, y, w, h = rect
            if w >= prod_w and h >= prod_h:
                if self._can_place_(stock, (x, y), prod_size):
                    rect_area = w * h
                    area_diff = rect_area - prod_area
                    if area_diff < min_area_diff:
                        min_area_diff = area_diff
                        best_rect = rect

        return best_rect

    def reset(self):
        """Reset the policy to its initial state."""
        self.current_placements = []
        self.free_rectangles = {}  # Reset free rectangles

        # Initialize free rectangles for the first stock
        if self.initial_stocks:  # Assuming you have a way to access the initial stocks
            stock_w, stock_h = self._get_stock_size_(self.initial_stocks[0])
            self.free_rectangles[0] = [(0, 0, stock_w, stock_h)]  # Set the first stock

    def _place_guillotine(self, products, observation):
        """Guillotine placement strategy"""
        placements = []

        for prod in products:
            for _ in range(prod["quantity"]):
                placed = False

                # First try stocks that are already in use
                used_stocks = [idx for idx in range(len(observation["stocks"]))
                               if idx in self.free_rectangles and self.free_rectangles[idx]]
                unused_stocks = [idx for idx in range(len(observation["stocks"]))
                                 if idx not in used_stocks]

                # Try all used stocks first
                for stock_idx in used_stocks:
                    stock = observation["stocks"][stock_idx]
                    self._merge_rectangles(stock_idx)

                    # Try both orientations
                    for size in [prod["size"], prod["size"][::-1]]:
                        rect = self._find_best_area_fit(size, stock_idx, stock)
                        if rect:
                            placement = {
                                "stock_idx": stock_idx,
                                "size": size,
                                "position": (rect[0], rect[1])
                            }
                            placements.append(placement)

                            # Update free rectangles
                            free_rects = self.free_rectangles[stock_idx]
                            free_rects.remove(rect)
                            free_rects.extend(self._split_rectangle(rect, size))
                            self._merge_rectangles(stock_idx)

                            placed = True
                            break
                    if placed:
                        break

                # If not placed, try unused stocks
                if not placed:
                    for stock_idx in unused_stocks:
                        stock = observation["stocks"][stock_idx]

                        # Initialize free rectangles for new stock
                        stock_w, stock_h = self._get_stock_size_(stock)
                        self.free_rectangles[stock_idx] = [(0, 0, stock_w, stock_h)]

                        # Try both orientations
                        for size in [prod["size"], prod["size"][::-1]]:
                            rect = self._find_best_area_fit(size, stock_idx, stock)
                            if rect:
                                placement = {
                                    "stock_idx": stock_idx,
                                    "size": size,
                                    "position": (rect[0], rect[1])
                                }
                                placements.append(placement)

                                # Update free rectangles
                                free_rects = self.free_rectangles[stock_idx]
                                free_rects.remove(rect)
                                free_rects.extend(self._split_rectangle(rect, size))
                                self._merge_rectangles(stock_idx)

                                placed = True
                                break
                        if placed:
                            break

                if not placed:
                    break

        return placements

    def _place_best_fit(self, products, observation):
        """
        Best-Fit placement strategy: Place products in stocks to minimize wasted space.
        """
        placements = []

        for prod in products:
            for _ in range(prod["quantity"]):
                best_fit = None
                best_stock_idx = None
                min_wasted_space = float('inf')

                # Iterate through all stocks
                for stock_idx, stock in enumerate(observation["stocks"]):
                    stock_w, stock_h = self._get_stock_size_(stock)

                    # Initialize free rectangles for new stock if needed
                    if stock_idx not in self.free_rectangles:
                        self.free_rectangles[stock_idx] = [(0, 0, stock_w, stock_h)]

                    for rect in self.free_rectangles[stock_idx]:
                        x, y, w, h = rect

                        # Check both orientations
                        for size in [prod["size"], prod["size"][::-1]]:
                            prod_w, prod_h = size

                            if w >= prod_w and h >= prod_h:
                                wasted_space = (w * h) - (prod_w * prod_h)

                                if wasted_space < min_wasted_space:
                                    min_wasted_space = wasted_space
                                    best_fit = (rect, size, (x, y))
                                    best_stock_idx = stock_idx

                if best_fit:
                    rect, size, position = best_fit
                    stock_idx = best_stock_idx

                    # Add placement
                    placement = {
                        "stock_idx": stock_idx,
                        "size": size,
                        "position": position
                    }
                    placements.append(placement)

                    # Update free rectangles
                    self.free_rectangles[stock_idx].remove(rect)
                    self.free_rectangles[stock_idx].extend(self._split_rectangle(rect, size))
                    self._merge_rectangles(stock_idx)
                else:
                    break  # If no valid placement found, stop trying to place this product

        return placements